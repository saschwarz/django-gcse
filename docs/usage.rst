========
Usage
========

To use django-gcse in a project::

	import django-gcse

'django-gcse' dynamically generates the files used by Google Custom Search Engines (CSE) to implement a `Linked Custom Search Engine <https://www.google.com/cse/docs/cref.html>`_. Use the Django admin screens to enter the URLs to be searched (Annotations) and their search refinement Labels. Then you configure your Google CSE to retrieve the Annotations from your 'django-gcse' URL. 

'django-gcse' makes it easy to maintain your Annotations.


You can import an existing CSE along with it's Annotations or create a new one and populate it all from within the 'django-gcse' admin screens.

1. First `create a Google Custom Search Engine <https://www.google.com/cse/all>`_ and configure the settings as you desire.

2. Download the CSE context from the `Advanced tab <https://www.google.com/cse/setup/advanced>`_.
