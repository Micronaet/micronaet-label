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


class ResPartner(orm.Model):
    """ Model name: Partner parameter
    """

    _inherit = 'res.partner'

    _columns = {
        'partner_pallet_logo': fields.boolean('Logo partner pallet',
            help='Utilizza il logo del partner sulla etichetta pallet'),
        'company_pallet_name': fields.char('Nome azienda pallet', size=80,
            help='Nome azienda sulla etichetta pallet'),
        }


class SaleOrderLine(orm.Model):
    """ Model name: Line in pallet
    """

    _inherit = 'sale.order.line'

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def pallet_unlink_line(self, cr, uid, ids, context=None):
        """ Unlink pallet
        """
        return self.write(cr, uid, ids, {
            'pallet_id': False,
            }, context=context)

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
        'default_q_x_pallet': fields.integer('Default q x pallet'),
        'pallet_ids': fields.one2many('label.pallet', 'mrp_id', 'Pallet'),
        }
