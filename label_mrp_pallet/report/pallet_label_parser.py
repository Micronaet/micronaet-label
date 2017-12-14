#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2010-2012 Associazione OpenERP Italia
#   (<http://www.openerp-italia.org>).
#   Copyright(c)2008-2010 SIA "KN dati".(http://kndati.lv) All Rights Reserved.
#                   General contacts <info@kndati.lv>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import os
import sys
import logging
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)

_logger = logging.getLogger(__name__)


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({            
            'get_report_single_label': self.get_report_single_label,
            })
            
    def get_report_single_label(self, o):
        ''' Prepare report pallet for element
        '''
        res = {}
        default_q_x_pallet = o.default_q_x_pallet
        for item in sorted(o.order_line_ids, key=lambda x: x.sequence):
            # -----------------------------------------------------------------
            # Has pallet label:
            # -----------------------------------------------------------------
            if not item.partner_id.has_pallet_label:
                continue
            product = item.product_id
            
            # -----------------------------------------------------------------
            # Get q per pallet:
            # -----------------------------------------------------------------
            # Data used in quotation:
            try:
                item_per_pallet = int(product.item_per_pallet)
            except:
                item_per_pallet = 0
            
            # Data used for label:
            q_x_pallet = product.q_x_pallet or item_per_pallet or \
                default_q_x_pallet
            if not q_x_pallet:
                raise osv.except_osv(
                    _('Q x pallet 0'), 
                    _('No q x pallet in %s' % product.default_code),
                    )
            
            # -----------------------------------------------------------------
            # Partner address 
            # -----------------------------------------------------------------
            key = (
                item.partner_id, 
                item.order_id.destination_partner_id, 
                item.product_id,
                item.order_id,
                )

            if key not in res:
                res[key] = [q_x_pallet, item.product_uom_qty]

        pallet = []

        for key in sorted(res, key=lambda x: (
                x[0].name, 
                x[1].name if x[1] else '', 
                x[2].default_code,
                )):
                
            q_x_pallet, total = res[key]
            loop = int(total / q_x_pallet)
            if int(total) % q_x_pallet != 0:
                loop += 1
            #remain = total
            for i in range(0, loop):
                #remain -= q_x_pallet
                order_ref = key[3].client_order_ref.split('|')
                if len(order_ref) == 2:
                    order_ref = order_ref[-1]
                else:
                    order_ref = ''

                if key[0].partner_pallet_logo: 
                    # Use partner logo
                    image = key[0].label_image 
                else:
                    # Use company logo:
                    image = key[2].company_id.partner_id.label_image    
                    
                pallet.append((
                    key, 
                    0, #remain if remain > 0 and remain < q_x_pallet else \
                    #    q_x_pallet,
                    order_ref,
                    image,
                    # name (could be forced)
                    (key[0].company_pallet_name or key[0].name).strip(), 
                    ))
        return pallet
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
