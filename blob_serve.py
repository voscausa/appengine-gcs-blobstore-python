#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext.webapp import blobstore_handlers
import urllib
import logging


class UseBlobstore(blobstore_handlers.BlobstoreDownloadHandler):
    """ use the blobstore to download a GCS blobfile """

    def get(self, resource):
        """ Example: /use_blobstore/<blob_key>?save_as=<gcf.filename>
            GCS files cannot use the BlobInfo class. We have to use: save_as=<bf.filename>
        """

        save_as = self.request.get('save_as', default_value=None)
        logging.info('UseBlobstore download blob : ' + save_as)

        blob_key = str(urllib.unquote(resource))
        self.send_blob(blob_key, save_as=save_as)