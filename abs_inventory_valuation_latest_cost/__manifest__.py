# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2018-Today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

{
    'name'    : "Inventory Valuation based on Latest Purchase Cost",
    'author'  : 'Ascetic Business Solution',
    'category': 'Inventory/Reporting',
    'summary' : "Inventory valuation based on the latest purchase cost",
    'license' : 'AGPL-3',
    'website' : 'http://www.asceticbs.com',
    'description': """
        This module adds a 'Latest Purchase Cost' field to stock quants,
        automatically calculated from the most recent confirmed purchase order.
        A scheduled action updates the values daily.
    """,
    'version' : '19.0.1.0.0',
    'depends' : ['base', 'stock', 'purchase'],
    'data'    : [
        'security/ir.model.access.csv',
        'views/stock_quant_view.xml',
        'views/stock_quant_schedular_view.xml',
    ],
    'images'      : ['static/description/banner.png'],
    'installable' : True,
    'application' : False,
    'auto_install': False,
}
