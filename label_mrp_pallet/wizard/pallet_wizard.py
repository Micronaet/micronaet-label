# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


import os
import sys
import logging
import openerp
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)


class LabelPalletGenerateWizard(orm.TransientModel):
    ''' Generate pallet label wizard
    '''
    _name = 'label.pallet.generate.wizard'

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def new_pallet(self, cr, uid, mrp, context=None):
        ''' New pallet
        '''
        # Search last number
        maximum = 0
        for pallet in mrp.pallet_ids:
            if pallet.code > maximum:
                maximum = pallet.code
        maximum += 1
        
        # Create pallet:
        pallet_pool = self.pool.get('label.pallet')
        pallet_id = pallet_pool.create(cr, uid, {
            'code': maximum,
            'mrp_id': mrp.id,
            }, context=context)

        return pallet_id

    # -------------------------------------------------------------------------
    # Wizard button event:
    # -------------------------------------------------------------------------
    def action_assign(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
                     
        if context is None: 
            context = {}        

        # Pool used:        
        mrp_pool = self.pool.get('mrp.production')
        line_pool = self.pool.get('sale.order.line')

        mrp_id = context.get('active_id') # mrp_id
                
        wizard_browse = self.browse(cr, uid, ids, context=context)[0]
        mrp_proxy = mrp_pool.browse(cr, uid, mrp_id, context=context)
        
        # Read parameters:
        mode = wizard_browse.mode
        partner = wizard_browse.partner_id

        if mode == 'unassigned': # all remain
            unassigned_ids = []
            for line in mrp_proxy.order_line_ids:
                if not line.pallet_id:
                    unassigned_ids.append(line.id)
                
            if unassigned_ids:
                pallet_id = self.new_pallet(
                    cr, uid, mrp_proxy, context=context)
                line_pool.write(cr, uid, unassigned_ids, {
                    'pallet_id': pallet_id,
                    }, context=context)
                
        return {'type': 'ir.actions.act_window_close'}

    _columns = {
        'partner_id': fields.many2one(
            'res.partner', 'Partner', help='Pallet only for partner'),
        'mode': fields.selection([
            ('address', 'Split in address'),
            ('all', 'All in one'),
            ('unassigned', 'All unassigned'),            
            ], 'Mode', help='Split mode')
        }
        
    _defaults = {
        'mode': lambda *x: 'unassigned',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


