================
Development Tips
================

Release package
---------------

Create a specific release
~~~~~~~~~~~~~~~~~~~~~~~~~

The following steps are required to release a package.

* (Create a stable branch if necessary)
* Add a signed tag to the repository

  .. code-block:: console

     git checkout stable/xxxx (if necessary)
     git tag -s <version number>
     git show <version number>
     git push gerrit <version number>

  .. warning::

     Before pushing a tag to gerrit, you are strongly suggested to
     test whether a generated package works as expected.

     .. code-block:: console

        git checkout <version number>
        python setup.py sdist
        pip install dist/networking-nec-<version number>.tar.gz

  To push a tag to gerrit, you must be a member of
  ``networking-nec-release`` gerrit group.

* Push a release package to PyPI.

  .. code-block:: console

     git checkout <version number>
     python setup.py sdist upload

  Once the upload succeeded, you can find a new release at
  https://pypi.python.org/pypi/networking-nec.

  Before uploading a package to PyPI, you need to create your PyPI
  account and prepare a proper credential file ``~/.pypirc`` like below.

  .. code-block:: ini

     [distutils]
     index-servers =
       pypi

     [pypi]
     repository=https://pypi.python.org/pypi
     username=<your username>
     password=<your password>

Create a stable branch
~~~~~~~~~~~~~~~~~~~~~~

The detail is available at:
http://docs.openstack.org/infra/manual/drivers.html#release-management.

To create a (stable) branch, you must be a member of
``networking-nec-release`` gerrit group.

More information
~~~~~~~~~~~~~~~~

Most of the release process is explained in
`OpenStack Infrastructure User Manual
<http://docs.openstack.org/infra/manual/>`_.

Requirements update
-------------------

In OpenStack projects, requirements.txt and test-requirements.txt
should be synced with ``global-requirements.txt`` in
http://git.openstack.org/cgit/openstack/requirements/tree/.

To sync requirements manually:

1. Check out requirements repository:

   .. code-block:: console

      git clone https://git.openstack.org/openstack/requirements

2. Run update.py:

   .. code-block:: console

      cd requirements
      tox -e venv -- python update.py <networking-nec top directory>

To sync it automatically, you need to:

* setup the jenkins job ``gate-{name}-requirements``
  (it is usually unnecessary as ``python-jobs`` contains it),
* add ``check-requirements`` to ``zuul/layout.yaml`` in
  project-config, and
* add ``openstack/networking-nec`` to ``projects.txt`` in the
  requirements project.

Documentation
-------------

Build documentation
~~~~~~~~~~~~~~~~~~~

To build the documentation:

.. code-block:: console

   tox -e docs

and the generated documentation will be found under ``doc/build/html``.

Publish documentation
~~~~~~~~~~~~~~~~~~~~~

The document is hosted by `Read The Docs <https://readthedocs.org/>`__
and the documentation is available at
http://networking-nec.readthedocs.org/en/latest/.

To publish the latest documentation,
visit the `project page <https://readthedocs.org/projects/networking-nec/>`__,
go to **Builds** and click **Build version** after selecting **latest**.
After completing the build, the status will be **Passed** and
you can see the new document.
If the build fails, investigate reasons of the failure.

Third party CI
--------------

* The master information about setting up and operating a third party CI
  is available at
  http://docs.openstack.org/infra/system-config/third_party.html.
  It is better to check this site regularly.

* The status of your third party CI system should be available at
  https://wiki.openstack.org/wiki/ThirdPartySystems.
  For example, you have a planned power blackout, it is encouraged
  to update the corresponding page.
