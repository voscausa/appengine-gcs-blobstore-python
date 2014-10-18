#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import webapp2
from google.appengine.ext import blobstore
from google.appengine.api import app_identity, images
from google.appengine.api import lib_config
import cloudstorage as gcs
from google.appengine.ext import ndb
import os
import mimetypes
import zipfile
import logging

# to use cloudstorage include appengine-gcs-client-python-r127.zip in your project

config = lib_config.register('blob_files', {
    'USE_BLOBSTORE': True,
    'ARCHIVE_PATH': '/archives/BlobFiles.zip',
    'UTF_8_FILE_EXTENSIONS': ['js', 'css', 'html', 'txt', 'text', 'py', 'xml']
})


class BlobFiles(ndb.Model):
    """ Contains GCS files names and serving urls for the app_default_bucket
        GCS files can have a blobkey. A GCS blobkey does NOT have a BlobInfo object.
        A Blobfile entity is like a blobstore.BlobInfo object
    """

    filename = ndb.StringProperty()  # unique (folder not part of filename, key and id)
    extension = ndb.ComputedProperty(lambda self: self.filename.rsplit('.', 1)[1].lower())
    folder = ndb.StringProperty(default='/')
    gcs_filename = ndb.StringProperty(required=True)  # /<bucket></folder[>/self.filename
    blobkey = ndb.ComputedProperty(lambda self: blobstore.create_gs_key('/gs' + self.gcs_filename))
    serving_url = ndb.StringProperty(required=True)
    modified = ndb.DateTimeProperty(auto_now=True)
    created = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def new(cls, filename, bucket=None, folder='/'):
        """ filename is the key, which makes an entity unique. But it's not allowed to overwrite a
            BlobFiles entity, if the new gcs_filename is not equal to the existing gcs path
            use_blobstore controls the type of serving_url. True: use Blobkey; False: use gcs_filename
        """

        gcs_filename = '/%s%s/%s' % (bucket or app_identity.get_default_gcs_bucket_name(), folder, filename)
        bf = cls.get_by_id(filename)
        if bf and gcs_filename != bf.gcs_filename:
            logging.error('new gcs_filename: %s already exists as gcs_filename: %s' % (gcs_filename,  bf.gcs_filename))
            return None

        return BlobFiles(id=filename, filename=filename, folder=folder, gcs_filename=gcs_filename)

    def properties(self):

        return gcs.stat(self.gcs_filename)

    def blob_read(self):
        """ read binary blob from google cloud storage """

        try:
            with gcs.open(self.gcs_filename) as f:
                return f.read()
        except gcs.NotFoundError, e:
            logging.warning('GCS file %s NOT FOUND : %s' % (self.gcs_filename, e))
            return None

    def blob_reader(self):
        """ a BlobInfo like open returns a BlobReader """

        return blobstore.BlobReader(blobstore.BlobKey(self.blobkey))

    def blob_write(self, blob):
        """ update google cloud storage bf entity """

        content_type = mimetypes.guess_type(self.filename)[0]
        if not content_type:
            logging.warning('Mimetype not guessed for: %s', self.filename)

        if content_type and self.extension in config.UTF_8_FILE_EXTENSIONS:
            content_type += b'; charset=utf-8'
        try:
            with gcs.open(self.gcs_filename, 'w', content_type=content_type or b'binary/octet-stream',
                          options={b'x-goog-acl': b'public-read'}) as f:
                f.write(blob)
            return self.gcs_filename
        except Exception, e:
            raise Exception('Blob write failed for %s, exception: %s. Additional info was logged' % (self.filename, str(e)))

    @classmethod
    def list_gcs_file_names(cls, bucket=None, folder='/'):
        """ Example usage :  for gcs_filename, filename in BlobFiles.list_gcs_file_names(folder='/upload') """

        for obj in gcs.listbucket('/%s%s' % (bucket or app_identity.get_default_gcs_bucket_name(), folder)):
            pbf = cls._query(cls.gcs_filename == obj.filename).get(projection=cls.filename)
            # yield result: the gcs_filename from GCS and the corresponding filename from BlobFiles
            yield obj.filename, (pbf.filename if pbf else '')

    def delete(self):
        """ delete filename in GCS and BlobFiles """

        try:
            gcs.delete(self.gcs_filename)
        except gcs.NotFoundError, e:
            logging.warning('GCS file %s NOT FOUND : %s' % (self.gcs_filename, e))
        return self.key.delete()

    def _pre_put_hook(self):
        """ ndb hook to save serving_url """

        if self.extension in ['jpeg', 'jpg', 'png', 'gif', 'bmp', 'tiff', 'ico']:  # image API supported formats
            # High-performance dynamic image serving
            self.serving_url = images.get_serving_url(self.blobkey, secure_url=True)
        elif webapp2.get_request().get('use_blobstore', default_value=config.USE_BLOBSTORE) in ['T', True]:
            # Blobstore: GCS blob keys do not have a BlobInfo filename
            self.serving_url = '/use_blobstore/%s?save_as=%s' % (self.blobkey, self.filename)
            # bf.serving_url = '/use_blobstore/%s?save_as=%s' % (blobstore.create_gs_key('/gs' + gcs_file_name), bf.filename)
        elif os.environ['SERVER_SOFTWARE'].startswith('Development'):
            # GCS url: this SDK feature has not been documented yet !!!
            self.serving_url = '/_ah/gcs%s' % self.gcs_filename
        else:
            # GCS url: because of HTTPS we cannot use a cname redirect or use the use_blobstore option
            self.serving_url = 'https://storage.googleapis.com%s' % self.gcs_filename


def blob_archive(new_bf=None):
    """ bonus: save all BlobFiles in a zip archive """

    @ndb.tasklet
    def callback(bf_key):
        """ key_only query and get() lookup for entity consistency """

        bf = yield bf_key.get_async()
        raise ndb.Return(bf)

    def blobfiles(insert, archive_key):
        """ We do not use ancestor queries. This Generator takes care of index and entity inconsistencies
            https://cloud.google.com/developers/articles/balancing-strong-and-eventual-consistency-with-google-cloud-datastore/
        """

        for bf in BlobFiles.query().filter(BlobFiles.key != archive_key).map(callback, keys_only=True):
            if insert and new_bf.key == bf.key:
                insert = False  # no index inconsistency
            yield bf

        # if the new_bf entity is not yet present in BlobFiles (due to index inconsistencies), it will be inserted here
        if insert:
            yield new_bf

    # add all files to archive, except the archive zipfile itself which has a reserved name (BlobFiles key)
    (archive_folder, _, archive_file) = config.ARCHIVE_PATH.rpartition('/')

    if new_bf and new_bf.filename != archive_file:

        new_zf = BlobFiles.new(archive_file, folder=archive_folder)
        with gcs.open(new_zf.gcs_filename, 'w', content_type=b'multipart/x-zip',
                      options={b'x-goog-acl': b'public-read', b'cache-control': b'private, max-age=0, no-cache'}) as nzf:

            # nzf is a cloudstorage.storage_api.StreamingBuffer, which can be pickled to append data in a chained task
            with zipfile.ZipFile(nzf, 'w') as zf:
                for each in blobfiles(new_bf is not None, new_zf.key):
                    # We also could have used : each.blob_read()
                    logging.info(each.filename)
                    blob = each.blob_reader().read()
                    zf.writestr(each.filename.encode('utf-8'), blob)

        new_zf.put_async()
    else:
        new_zf = new_bf

    return new_zf