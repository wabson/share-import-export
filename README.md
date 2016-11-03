Share Import/Export Tools
=========================

Author: Will Abson

The Share Import/Export tools provide a set of Python scripts for importing and
exporting site-based content and user information held within Alfresco Share,
and also provide some sample demo content.

The tools were written to help set up demonstration environments quickly, reliably and consistently. Others have used them for migrating sites from one system to another and some enhancements have been made to better support this. However we do not recommend using the scripts for creating backups.

The scripts connect to Alfresco Share via HTTP, so can be used against a local or
a remote instance of Share, or even the public [MyAlfresco](https://my.alfresco.com/) service.

Contribution: Mikel Asla

* Added support to import category trees
* Minor fixes
  * Fixed encoding issue exporting categories with non-ascii characters
  * Fixed import-groups.py not to create users as groups (when found by the script as children of group being created)
  * Additional argument for import-users.py to support default_email as a workaround to importing users with no email specified

What can be imported/exported?
------------------------------

  * Sites
    * Site configurations
    * Site members (users only at present)
    * Site dashboards, including dashlet configuration
    * All content held within the site
    * Records Management sites (must have RM installed)
    * Web Quick Start sites (must have WQS installed)
    * Document categories and tags (specify `--export-tags` and `--import-tags`)

  * Users
    * All profile information, including profile images
    * User dashboard configurations
    * User preferences
    * User groups and group memberships

What is not imported/exported?

  * User passwords (passwords are set to the same value as the username by default, since they cannot be exported)
  * User passwords and account enabled flags (all accounts enabled)
  * Activity feed entries
  * File system-level customisations (e.g. custom dashlets) and configuration

Requirements
------------

The scripts work with fully with versions 3.3, 3.4 and 4.x of Alfresco, with additional limited support for previous versions of 3.x. No additional customisations are needed in Alfresco or Share, so you can export data from existing systems without any fuss.

*Note: in Alfresco 4.2 and greater the new CSRF filter blocks some of the requests made by the tools and must be temporarily disabled - see Troubleshooting, below, for details of how to do this.*

[Python](http://www.python.org/) 2.6 or greater is required to run the scripts, with Python 2.7 recommended for packaging site bootstrap packages. At present Python 3.x is **not supported**.

Usage
-----

The tools are supplied as a set of executable Python scripts that can be run from the command line. The general usage syntax is

    python script-name.py <parameters> <options>

This assumes that Python is set up on your system and installed in your system `PATH`.

You can use the `--help` option with any of the scripts mentioned below for information on the different parameters accepted.

### Importing Content

Sites and users can be imported from JSON files on your local system, and examples of these
are supplied in the `data` folder.

To import one of the sample sites, change into the project root directory at a
command prompt. Then type the following

    python import-site.py data/sites/branding.json \
      --create-missing-members \
      --users-file=data/cloud-users.json \
      --username=username --password=password \
      --url=<share-url>

For more site definitions you can choose between the files `images.json`, `usersgroup2010.json`, `exec1.json` and `rm.json`.

After importing the site(s) you should see them listed when you log in to Alfresco Share as Paul Hampton (`phampton`/`phampton`).

You must either create the user accounts of all site members (see below) before creating sites, or specify the
`--create-missing-members` and `--users-file` arguments, otherwise the site import script will
fail when it tries to add site members which do not exist.

If your site has group-based members then you must import these separately first, using the
`import-groups.py` script.

The `username` and `password` values must match those of an existing admin user on the system
with the Share URL `share-url`.

If you are running a local instance of Alfresco and wish to run the import as the admin user
using the default password, you can omit the `--username`, `--password` and `--url` arguments.

### Importing users

If you only want to import users without any site content, you can import users defined in
a JSON users file. An example `cloud-users.json` is supplied in the data folder.

Change into the project root directory at a command prompt. Then type the following

    python import-users.py data/cloud-users.json \
      --create-only \
      --username=username \
      --password=password \
      --url=<share-url>

The `username` and `password` values must match those of an existing admin user on the system
with the Share URL `share-url`.

If you are running a local instance of Alfresco and wish to run the import as the admin user
using the default password, you can omit the `--username`, `--password` and `--url` arguments.

To set user preferences and upload profile images, remove the `--create-only` argument from
the command. Note that on Windows systems, the large number of HTTP requests may cause
problems.

If you have problems you can constrain the list of users that are created using the `--users=`
argument, e.g.

    python import-users.py data/cloud-users.json \
      --users=phampton,bburchetts,cknowl,iwargrave,jtalbot,nswallowfield,sclark

### Importing a site

Once you have imported your users you can create a site. You must supply a site JSON file from
which information about the site will be read. Several examples are supplied in the `data/sites` folder.

To import the `branding` site and its contents, run the following command from a terminal.

    python import-site.py data/branding.json --username=username --password=password --url=<share-url>

The command will create the site and set it's configuration, members and dashboard configuration.
Finally it will import the site content from any associated ACP files.

### Exporting Content

#### Exporting a site

Run the following command from a terminal

    python export-site.py siteid file.json --username=username --password=password --url=<share-url>

The `siteid` argument is the URL name of the site in Share. If you are not sure what this means
you can use the full URL of the site dashboard page instead.

The second argument is the name of the file where the site information will be stored in JSON
format.

To also export the site content in ACP format, add the `--export-content` flag to the command. You
must have *Contributor* permission or greater on the site in order to export content.

#### Exporting users

Run the following command from a terminal

    python export-users.py file.json --username=username --password=password --url=<share-url>

### Removing Content

If something goes wrong when importing content you may need to remove the old definitions before
trying again.

#### Removing a site

You can remove a single site from the system by specifying the site ID or URL of the dashboard
page.

    python purge-site.py siteid --username=username --password=password --url=<share-url>

### Removing users

This will remove ALL the users specified in the local file `users-file.json` from Alfresco. Use this with extreme caution!

    python purge-users.py users-file.json --username=username --password=password --url=<share-url>

To remove only a few selected users, add the `--users=user1,user2` flag to the command.

#### Migrating a complete Site (including categories)

This are the steps needed in order to migrate a complete Site of Alfresco including categories and tags. This procedure has been checked with Alfresco Community 4.2.f as the origin system and Alfresco Community 201605-GA as the destination.

First, we need to export the Site in the origin instance, along with **all** users, groups and categories (and also tags)

    python export-groups.py exported-groups.json --skip-groups=EMAIL_CONTRIBUTORS,ALFRESCO_ADMINISTRATORS
    python export-users.py exported-users.json
    python export-categories.py exported-categories.json
    python export-site.py siteid exported-site.json --export-content --export-tags
 
And obviously now we need to import all this in the destination Alfresco instance

    python import-groups.py exported-groups.json
    python import-users.py exported-users.json (if executed in first place memberships are not processed)
    python import-categories.py exported-categories.json
    python import-site.py exported-site.json --create-missing-members --users-file exported-users.json --import-tags

Also all above commands need this other arguments, omitted for clarity

    --username=username --password=password --url=<share-url>

Troubleshooting
---------------

### ServletException: Possible CSRF attack noted when comparing token in session and request header

The CSRF filter [introduced in Alfresco 4.2](http://blogs.alfresco.com/wp/ewinlof/2013/03/11/introducing-the-new-csrf-filter-in-alfresco-share/) blocks some of the web scripts used by the scripts. It must be disabled so that the scripts can be used, by uncommenting or adding the following config in your `share-config-custom.xml` file.

    <config evaluator="string-compare" condition="CSRFPolicy" replace="true">
       <filter/>
    </config>

Once you have completed the import/export you should remove this configuration to re-enable the filter.

### The authority with name xxxxx could not be found

When you try to import a site you see the following error reported in the console:

    alfresco.SurfRequestError: Spring Surf Error 400 (Bad Request): "The authority with name xxxxx could not be found."

This means that one of the members of the site could not be found in the destination system, and therefore they could not be added to the site. Either add the missing users, or add the `--skip-missing-members` flag to your command to suppress the errors.

### Association name {http://www.alfresco.org/model/content/1.0}thumbnails is not valid

When you try to import a site you see the following error reported in the console:

    alfresco.SurfRequestError: Spring Surf Error 500 (Internal Server Error): "Failed to import package at line 128; column 34 due to error: Association name {http://www.alfresco.org/model/content/1.0}thumbnails is not valid; cannot find in Repository dictionary"

This occurs because the original `cm:thumbnails` association used prior to version 3.2 of Alfresco is no longer present in newer versions as the rendition service is used instead.

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

How does it work?
-----------------

The scripts mimic a web browser logging into the Share web application, then invoke a number of mostly JSON-based web scripts to read and write data to and from the application. JSON is also used as the format for storing exported metadata and user information, since it is well-structured, human readable and lightweight. Python has strong support for JSON data via the `json` module. [ACP format](http://wiki.alfresco.com/wiki/ACP) is used to package up site content.

Credits
-------

Thanks to Paul Hampton for providing the sample content
