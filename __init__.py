# -*- coding: utf-8 -*-
"""
QGIS Work Log plugin – project-linked diary / lab notebook.
"""

__version__ = "1.4.12"


def classFactory(iface):
    """Load TerraAnalytica WorkLogPlugin class from file worklog_plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .worklog_plugin import WorkLogPlugin
    return WorkLogPlugin(iface)
