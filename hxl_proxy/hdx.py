"""Integration support with HDX."""

import ckanapi

ckan_url = 'https://data.hdx.rwlabs.org'

def get_hdx_datasets(tag='hxl'):
    """Get datasets from CKAN using a tag."""
    ckan = ckanapi.RemoteCKAN(ckan_url)
    tag_info = ckan.action.tag_show(id='hxl')
    return tag_info.get('packages')

