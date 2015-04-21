#!/usr/bin/python
# -*- coding: utf-8 -*-

import webapp2
from google.appengine.api import app_identity
from google.appengine.api import urlfetch
from google.appengine.runtime import DeadlineExceededError
import json
import logging

SCOPE_FULL_CONTROL = 'https://www.googleapis.com/auth/devstorage.full_control'
default_bucket = app_identity.get_default_gcs_bucket_name()


def acl_fetch(fetch_function):

    retry = 0
    while retry <= 1:
        try:
            access_token = app_identity.get_access_token(SCOPE_FULL_CONTROL)[0]
            headers = {'Authorization': 'OAuth %s' % access_token, 'Content-Type': 'application/json'}
            response = fetch_function(headers)

            if response.status_code != 200:
                logging.warning('acl_fetch response : %s content: %s' % (response.status_code, str(response.content)))
                return response.status_code
            else:
                logging.info(response.content)
                return 0
        except (urlfetch.DownloadError, DeadlineExceededError, app_identity.BackendDeadlineExceeded):
            logging.warning('download or deadline retry %d ' % (retry + 1))
            retry += 1
    return None


def insert_gcs_user_acl(bucket_object, e_mail):
    """ set gcs object access for e_mail. e-mail must be a valid google account or response_code = 400
        Download object : https://console.developers.google.com/m/cloudstorage/b/gcs-blobstore.appspot.com/o/codes.csv
    """

    url = 'https://www.googleapis.com/storage/v1/b/%s/o/%s/acl' % (default_bucket, bucket_object)
    payload = json.dumps(dict(entity='user-' + e_mail, role='READER'))

    def _insert_fetch(headers):

        return urlfetch.fetch(url, method=urlfetch.POST, payload=payload, headers=headers)

    response = acl_fetch(_insert_fetch)
    if response:
        logging.error('insert_gcs_user_acl for %s : %s response : %d' % (bucket_object, e_mail, response))
    return response


def delete_gcs_user_acl(bucket_object, e_mail, allow_404=False):
    """ delete gcs object access for ec_user. e-mail must be a valid google account or response_code = 400
        EC-user
    """

    url = 'https://www.googleapis.com/storage/v1/b/%s/o/%s/acl/user-%s' % (default_bucket, bucket_object, e_mail)

    def _delete_fetch(headers):

        return urlfetch.fetch(url, method=urlfetch.DELETE, payload=None, headers=headers)

    response = acl_fetch(_delete_fetch)
    if response and response != 204 and (response == 404 and not allow_404):
        logging.error('delete_gcs_user_acl for %s : %s response : %d' % (bucket_object, e_mail, response))
    return response


class InsertAcl(webapp2.RequestHandler):

    def get(self):

        bucket_object = 'codes.csv'
        e_mail = self.request.get('e_mail', default_value=None)
        if not e_mail:
            self.response.write('No value provided for argument e_mail')
            return

        response = insert_gcs_user_acl(bucket_object, e_mail=e_mail)
        if response == 0:
            self.response.write('<p>TestAcl finished. Authenticated user : %s can now download the object using<br>' % e_mail)
            download_link = 'https://console.developers.google.com/m/cloudstorage/b/%s/o/%s' % (default_bucket, bucket_object)
            self.response.write('<br><a href="%s">%s</a></p>' % (download_link, download_link))
            return

        self.response.write('TestAcl finished : %s' % str(response))


class DeleteAcl(webapp2.RequestHandler):

    def get(self):

        bucket_object = 'codes.csv'
        e_mail = self.request.get('e_mail', default_value=None)
        if not e_mail:
            self.response.write('No value provided for argument e_mail')
            return

        response = delete_gcs_user_acl(bucket_object, e_mail, allow_404=True)
        self.response.write('Delete finished : %s' % str(response))