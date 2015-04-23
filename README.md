## App Engine cloudstorage blobstore replacement using SDK and GAE production

This code shows how to read and write blobs and how to create a blob serving url (GCS host or blobkey).  
Writing blob files to GCS is a replacement for the deprecated blobstore.Files API.

The blob files can be images or other files like html, css, js and pdf.  
The free default bucket in Google Cloud Storage (GCS) is used to store the blobs.  
From the docs: An application can use the [default GCS bucket](https://developers.google.com/appengine/docs/python/googlecloudstorageclient/activate#Using_the_Default_GCS_Bucket), which provides an already configured bucket with [free quota](https://developers.google.com/appengine/docs/quotas#Default_Gcs_Bucket).

The code always uses the Images get_serving_url for images (gif/png/jpg).  
This image serving url allows dynamic resizing and cropping.  
The use_blobstore option configures the serving_url type for non-images.  
The use_blobstore default (= True) can be overwritten in appengine_config.py

blob_upload contains the code to upload a file to cloudstorage:

    upload: https://<appid>.appspot.com/blob_upload
    or: http://localhost:8080/blob_upload

To serve the data, you can use in your Jinja HTML template:

    js:  <script type="text/javascript" src="{{ serving_url }}"></script>
    css: <link type="text/css" rel="stylesheet" href="{{ serving_url }}">
    pdf: <a href="{{ serving_url }}" target="_blank">Test PDF</a>
    img: <img  alt="{{ filename }}" src="{{ serving_url }}" />

In GAE production the serving url looks like:

    images: https://lhN.ggpht.com/NlCARAtN.........3NQW9ZxYpms=s698
    other:  https://storage.googleapis.com/default_bucket/file_name
    or a blobstore like url, when use_blobstore = True
    
And in the SDK:

    images: http://localhost:8080/_ah/img/encoded_gs_file:YXBwX2R......Y3Nz
    other:  https://localhost:8080/_ah/gcs/default_bucket/file_name
    or a blobstore like url, when use_blobstore = True
    Note: The SDK encoded_gs_file id = base64.urlsafe_b64encode(app_default_bucket/filename)

The benefits of use_blobstore = False (GCS host):

    - Cheaper and probably significantly faster. 
    - Google will serve the GCS files for you. The BlobstoreDownloadHandler is not used.
    - The filename is short and part of the serving_url.
    - But the hostname of the serving is always https://storage.googleapis.com/... (because of HTTPS)
 
This code was tested using App Engine SDK 1.9.13 and the GCS client library

GCS client library installation on Windows 7:

    C:\Python27\scripts>pip install setuptools --no-use-wheel --upgrade
    C:\Python27\scripts>pip install GoogleAppEngineCloudStorageClient -t <my_app_directory_root>
    
## Insert or delete a READER acl-entry for an e-mail address using the Cloudstorage json API.

Examples in acl.py and api-test.py. api-test.py uses the [Pyhon API client for appengine](https://developers.google.com/api-client-library/python/start/installation#appengine)

The appengine Google Cloud Storage Client Library does not support setting or deleting ACL entries.

The App Engine development server supports the Cloud Storage Client. It doesn't support the json REST API.  
But the SDK can interact with the cloudstorage REST API in the Google Cloud using a service account.  
To make this work in the SDK, you have to use two options in development server:

    --appidentity_email_address=<developer service account e-mail address>
    --appidentity_private_key_path=<d:/.../gcs-blobstore.pem key>
    
The service account e-mail and a p12 key can be found in the Google Developers Console of your Cloud project:

    Google Developers Console -> API & Auth -> Create a new client ID for a service account and generate p12 key

Use openssl to convert the p12 in a RSA pem key. For windows use:

    openssl pkcs12 -in gcs-blobstore.p12  -nocerts -nodes -passin pass:notasecret | openssl rsa -out gcs-blobstore.pem  

[More docs about the service account SDK options](https://gist.github.com/pwalsh/b8563e1a1de3347a8066)