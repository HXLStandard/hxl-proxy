"""Uploaded file manager"""

import os
import tempfile

class UploadManager:
    """Manage file uploads."""

    def __init__(self, root_dir, base_url):
        """
        Constructor
        @param root_dir path to root file directory for uploads
        @param base_url path to the base URL for uploads
        """
        self.root_dir = root_dir
        self.base_url = base_url

    def create_upload(self, filename='data.csv'):
        """
        Make a unique new path for an upload.
        Will create a unique directory first, then put the file in it.
        @param filename the filename to use inside the directory (defaults to "data.csv")
        @return an Upload object representing the file upload
        """
        dir = tempfile.mkdtemp(dir=self.root_dir, prefix='')
        relpath = os.path.relpath(os.path.join(dir, filename), self.root_dir)
        return Upload(self.root_dir, self.base_url, relpath)


class Upload:
    """
    Abstract representation of a single file upload.
    """

    def __init__(self, root_dir, base_url, relpath):
        """
        Constructor
        @param root_dir path to root file directory for uploads
        @param base_url path to the base URL for uploads
        @param relpath the relative path of the upload inside the root_dir
        """
        self.root_dir = root_dir
        self.base_url = base_url
        self.relpath = relpath

    def get_path(self):
        """
        Get a path to the upload on the file system.
        """
        return os.path.join(self.root_dir, self.relpath)

    def get_url(self):
        """
        Get a URL for downloading the file.
        """
        return self.base_url + '/' + self.relpath

    def open(self, mode='r'):
        """
        Open the upload.
        @param mode the open mode (defaults to "r")
        """
        return open(self.get_path(), mode)

    def write(self, data):
        """
        Save data to the upload.
        @param data content to write to the upload (overwrites anything already there)
        """
        with self.open('wt') as output:
            output.write(data)

    def read(self):
        """
        Read data from the upload.
        @return the data from the upload
        """
        with self.open('rt') as input:
            return input.read()


