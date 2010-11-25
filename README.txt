What is included?

For sites:

Site pages
Dashboard configuration, including layout, contents and dashlet configuration
Site membership (users only at present)
Full site contents (via ACP, for export this must be done manually for now after running the tool)

What is not included

Custom security groups
Activity service data
Custom dashlets
Tag data??

Using the tools

Exporting a site

Run the following command from a terminal

python dump-site.py siteurl|siteid file.json [--username=username] [--password=username] [--url=username] [-d]

Exporting users



Removing a site

python purge-site.py siteurl|siteid [--username=username] [--password=username] [--url=username] [-d]


Importing a site

python bootstrap-site.py bootstrap-data/sites/rm.json --no-content
# Set up the current user as a repo admin and a records admin
python bootstrap-site.py bootstrap-data/sites/rm.json --no-create --no-members --no-dashboard --no-configuration

FAQ

When I try to import a site I see the following error reported:

alfresco.SurfRequestError: Spring Surf Error 400 (Bad Request): "The authority with name xxxxx could not be found."

This means that one of the members of the site could not be found in the destination system, and therefore they could not be added to the site. Either add the missing users, or add the --skip-missing-members flag to your command to suppress the errors.

When I try to import a site I see the following error reported:

alfresco.SurfRequestError: Spring Surf Error 500 (Internal Server Error): "Failed to import package at line 128; column 34 due to error: Association name {http://www.alfresco.org/model/content/1.0}thumbnails is not valid; cannot find in Repository dictionary"

This occurs because the original cm:thumbnails association used prior to version 3.2 of Alfresco is no longer present in newer versions as the rendition service is used instead.

To work around the issue, edit the XML descriptor file within the ACP package for that part of the site, and remove any cm:thumbnails associations or cm:thumbnailed aspects from the XML.

    <cm:content view:childName="cm:White Papers overview.pdf">
      <view:aspects>
        <sys:referenceable></sys:referenceable>
        <cm:titled></cm:titled>
        <cm:thumbnailed></cm:thumbnailed>
        ...
        <cm:versionable></cm:versionable>
      </view:aspects>
      <view:acl></view:acl>
      <view:properties>
      ...
      </view:properties>
      <view:associations>
        <cm:thumbnails>
          <cm:thumbnail view:childName="cm:doclib">
          ...
          </cm:thumbnail>
          <cm:thumbnail view:childName="cm:webpreview">
          ...
          </cm:thumbnail>
        </cm:thumbnails>
      </view:associations>
    </cm:content>


