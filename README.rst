=============================
django-gcse
=============================

.. image:: https://badge.fury.io/py/django-gcse.png
    :target: http://badge.fury.io/py/django-gcse

.. image:: https://travis-ci.org/saschwarz/django-gcse.png?branch=master
        :target: https://travis-ci.org/saschwarz/django-gcse

.. image:: https://coveralls.io/repos/saschwarz/django-gcse/badge.png?branch=master
        :target: https://coveralls.io/r/saschwarz/django-gcse?branch=master

.. image:: https://pypip.in/d/django-gcse/badge.png
        :target: https://crate.io/packages/django-gcse?version=latest


A django reusable application for maintaining websites/data for use with Google Custom Search Engines.

Documentation
-------------

The full documentation is at http://django-gcse.rtfd.org.

Quickstart
----------

Install django-gcse::

    pip install django-gcse

Then use it in a project::

    import gcse

Features
--------

* Import existing Custom Search Engines and their Annotations via URLs or files via a management command.

* Convert OPML files into Annotations for use in a Custom Search Engine via a management command.

* Share Annotations across multiple Custom Search Engines to ease maintenance.

* Browsable views for all Custom Search Engines, Annotations and Labels. Search the entries for a CSE using Google directly from the CSE view. Browsable views can be disabled.

* All entries can be managed via django admin screens.

* TODO:

  * Slugify Label and Annotation classes.

  * Admin handle ordering of FacetItems within a CustomSearchEngine.

  * Browsing views visible via settings configuration.

  * Create demo/tests with Annotations shared across multiple CSEs.

  * Define caching attributes on XML views sent to Google.

  * Admin access to management commands.
