#!/usr/bin/python
# -*- coding: utf-8 -*-

import webapp2
import json
import os
from oauth2client import appengine
from apiclient import discovery
import httplib2
import logging

SCOPE_FULL_CONTROL = 'https://www.googleapis.com/auth/devstorage.full_control'

# Use the default bucket in the cloud and not the local one from app_identity
default_bucket = '%s.appspot.com' % os.environ['APPLICATION_ID'].split('~', 1)[1]

http = httplib2.Http()
credentials = appengine.AppAssertionCredentials(scope=SCOPE_FULL_CONTROL)
http = credentials.authorize(http)


def api_insert_gcs_user_acl(bucket_object, e_mail):
    """ set gcs object access for e_mail. e-mail must be a valid google account or response_code = 400
        Download object : https://console.developers.google.com/m/cloudstorage/b/gcs-blobstore.appspot.com/o/codes.csv
    """

    client = discovery.build('storage', 'v1', http=http)
    req = client.objectAccessControls().insert(
        bucket=default_bucket,
        object=bucket_object,
        body=dict(entity='user-' + e_mail, role='READER')
    )

    resp = req.execute()
    logging.info(json.dumps(resp, indent=2))


class ApiInsertAcl(webapp2.RequestHandler):
    """ insert READER ACL user entry for bucket_object using the Cloud Storage API for appengine
        More: https://developers.google.com/resources/api-libraries/documentation/storage/v1/python/latest/
    """

    def get(self):

        bucket_object = 'codes.csv'
        e_mail = self.request.get('e_mail', default_value=None)
        if not e_mail:
            self.response.write('No value provided for argument e_mail')
            return

        logging.info(api_insert_gcs_user_acl(bucket_object, e_mail=e_mail))

        self.response.write('ApiInsertAcl finished')