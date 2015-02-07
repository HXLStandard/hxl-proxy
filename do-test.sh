#!/bin/sh

#https://docs.google.com/spreadsheets/d/1paoIpHiYo7dy_dnf_luUSfowWDwNAWwS3z4GHL2J7Rc/export?format=csv&id=1paoIpHiYo7dy_dnf_luUSfowWDwNAWwS3z4GHL2J7Rc&gid=2077872077
wget -q -O - 'http://127.0.0.1:5000/filter?format=csv&url=https%3A%2F%2Fdocs.google.com%2Fspreadsheets%2Fd%2F1paoIpHiYo7dy_dnf_luUSfowWDwNAWwS3z4GHL2J7Rc%2Fexport%3Fformat%3Dcsv%26id%3D1paoIpHiYo7dy_dnf_luUSfowWDwNAWwS3z4GHL2J7Rc%26gid%3D2077872077'
