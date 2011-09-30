Share Import/Export Tools
=========================

Author: Will Abson

The Share Import/Export tools provide a set of Python scripts for importing and 
exporting site-based content and user information held within Alfresco Share, 
together with sample content from the Alfresco Cloud Trial.

The scripts connect to Alfresco Share via HTTP, so can be used against a local or
a remote instance of Share.

What can be imported/exported?

  * Sites
    * Site configurations
    * Site members (users only at present)
    * Site dashboards, including dashlet configuration
    * All content held within the site
    * Records Management sites (must have RM installed)
    * Web Quick Start sites (must have WQS installed)

  * Users
    * All profile information, including profile images
    * User dashboard configurations
    * User preferences
    * User groups and group memberships

What is not imported/exported?

  * Document categories and tags (not currently supported by ACP format)
  * User passwords and account enabled flags (all accounts enabled)
  * Activity feed entries
  * File system-level customisations (e.g. custom dashlets) and configuration

Requirements
============

  * Python 2.6+ (http://www.python.org/)
  * Alfresco 3.3 or 3.4 target

Importing Content
=================

Sites and users can be imported from JSON files on your local system, and examples of these
are supplied in the 'data' folder.

To import one of the sample sites, change into the share-import-export directory at a 
command prompt. Then type the following

  python import-site.py data/sites/branding.json --create-missing-members --users-file=data/cloud-users.json --username=username --password=password --url=share-url

Note that you must either create the users (see below) before creating sites, or specify the 
--create-missing-members and --users-file arguments, otherwise the site import script will 
fail when it tries to add site members which do not exist.

If your site has group-based members then you must import these separately first, using the
import-groups.py script.

The 'username' and 'password' values must match those of an existing admin user on the system
with the Share URL 'share-url'.

If you are running a local instance of Alfresco and wish to run the import as the admin user
using the default password, you can omit the --username, --password and --url arguments.

Importing users
---------------

If you only want to import users without any site content, you can import users defined in 
a JSON users file. An example cloud-users.json is supplied in the data folder.

Change into the share-import-export directory at a command prompt. Then type the following

  python import-users.py data/cloud-users.json --create-only --username=username --password=password --url=share-url

The 'username' and 'password' values must match those of an existing admin user on the system
with the Share URL 'share-url'.

If you are running a local instance of Alfresco and wish to run the import as the admin user
using the default password, you can omit the --username, --password and --url arguments.

To set user preferences and upload profile images, remove the --create-only argument from 
the command. Note that on Windows systems, the large number of HTTP requests may cause
problems.

If you have problems you can constrain the list of users that are created using the --users=
argument, e.g.

  python import-users.py data/cloud-users.json --users=phampton,bburchetts,cknowl,iwargrave,jtalbot,nswallowfield,sclark

Importing a site
----------------

Once you have imported your users you can create a site. You must supply a site JSON file from
which information about the site will be read. Several examples are supplied in the data/sites folder.

To import the 'branding' site and its contents, run the following command from a terminal.

  python import-site.py data/branding.json --username=username --password=password --url=share-url

The command will create the site and set it's configuration, members and dashboard configuration.
Finally it will import the site content from any associated ACP files.

Exporting Content
=================

Exporting a site
----------------

Run the following command from a terminal

  python export-site.py siteid file.json --username=username --password=password --url=share-url

The 'siteid' argument is the URL name of the site in Share. If you are not sure what this means
you can use the full URL of the site dashboard page instead.

The second argument is the name of the file where the site information will be stored in JSON 
format.

To also export the site content in ACP format, add the --export-content flag to the command. You
must have Contributor permission or greater on the site in order to export content.

Exporting users
---------------

Run the following command from a terminal

  python export-users.py file.json --username=username --password=password --url=share-url

Removing Content
================

If something goes wrong when importing content you may need to remove the old definitions before
trying again.

Removing a site
---------------

You can remove a single site from the system by specifying the site ID or URL of the dashboard
page.

  python purge-site.py siteid --username=username --password=password --url=share-url

Removing users
--------------

This will remove ALL the users from the local file users-file.json. Use this with extreme caution!

  python purge-users.py users-file.json --username=username --password=password --url=share-url

To remove only a few selected users, add the --users=user1,user2 flag to the command.

Troubleshooting
===============

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


Credits
=======

Thanks to Paul Hampton for providing the sample content