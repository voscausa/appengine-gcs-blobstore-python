#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import webapp2
from webapp2_extras import jinja2
import blob_files
import blob_serve
import markdown
import logging
import os

GCS_UPLOAD_FOLDER = '/upload'
README = os.path.join(os.path.dirname(__file__), 'README.md')


class BaseHandler(webapp2.RequestHandler):

    def handle_exception(self, exception, debug):

        logging.exception(exception)
        self.response.write('<h3>A fatal error occurred.</h3>')

        if isinstance(exception, webapp2.HTTPException):
            self.response.set_status(exception.code)
        else:
            self.response.set_status(500)

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def render_template(self, template, **template_args):
        self.response.write(self.jinja2.render_template(template, **template_args))


class BlobUpload(BaseHandler):
    """ upload to cloudstorage and save serving_url in GcsFiles """

    def get(self):
        """ upload form """

        self.render_template('blob_upload.html', use_blobstore=blob_files.config.USE_BLOBSTORE)

    def readme(self):
        """ readme.md to html in base template """

        if self.request.method == 'GET':
            use_blobstore = blob_files.config.USE_BLOBSTORE
        else:  # POST
            use_blobstore = (True if self.request.get('use_blobstore') == 'T' else False)
        readme = markdown.markdown(open(README, 'r').read(), output_format='html5')  # options: markdown.__init__
        self.render_template('blob_upload.html', use_blobstore=use_blobstore, readme=readme)

    def post(self):
        """ upload the file en show file and archive links """

        context = dict(failed='No file data', use_blobstore=(True if self.request.get('use_blobstore') == 'T' else False))

        # read upload data, save it in GCS and a zip archive
        file_data = self.request.get("file", default_value=None)
        if file_data:

            filename = self.request.POST["file"].filename
            bf = blob_files.BlobFiles.new(filename, folder=GCS_UPLOAD_FOLDER)
            if bf:
                bf.blob_write(file_data)
                bf.put()
                logging.info('Uploaded and saved in default GCS bucket : ' + bf.gcs_filename)

                # update zip archive. make sure this (new) bf will be archived
                bzf = blob_files.blob_archive(new_bf=bf)

                context.update(dict(failed=None, bzf_url=bzf.serving_url, bzf_name=bzf.filename,
                                    bf_url=bf.serving_url, bf_name=bf.filename))
            else:
                context.update(dict(failed='Overwrite blocked. The GCS file already exists in another bucket and/or folder'))
        else:
            logging.error('No file data')

        self.render_template('blob_links.html', **context)

routes = [
    webapp2.Route(r'/blob_upload', handler=BlobUpload),
    webapp2.Route(r'/readme', handler='blob_upload.BlobUpload:readme'),
    ('/use_blobstore/([^/]+)?', blob_serve.UseBlobstore)
]
app = webapp2.WSGIApplication(routes=routes, debug=True)