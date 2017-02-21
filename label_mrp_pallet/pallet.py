# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class SaleOrderLine(orm.Model):
    """ Model name: Line in pallet
    """
    
    _inherit = 'sale.order.line'
    
    _columns = {
        'pallet_id': fields.many2one('label.pallet', 'Pallet'),
        }

class LabelPallet(orm.Model):
    """ Model name: LabelPallet
    """
    
    _name = 'label.pallet'
    _description = 'Label pallet'
    _rec_name = 'code'
    _order = 'code'
    
    _columns = {
        'code': fields.integer('Code', required=True),
        'mrp_id': fields.many2one(
            'mrp.production', 'Production', 
            required=False),
        'line_ids': fields.one2many(
            'sale.order.line', 'pallet_id', 'Order line'),
        }

class MrpProduction(orm.Model):
    """ Model name: MRP production
    """
    
    _inherit = 'mrp.production'
    
    _columns = {
        'pallet_ids': fields.one2many('label.pallet', 'mrp_id', 'Pallet'),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: