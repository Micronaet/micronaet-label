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
import logging
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from datetime import datetime, timedelta
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)

_logger = logging.getLogger(__name__)

class Parser(report_sxw.rml_parse):    
    def __init__(self, cr, uid, name, context):
        ''' Init parser script
        '''
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_label_list': self.get_label_list,
            'get_field_lang': self.get_field_lang,
            })
    
    def get_field_lang(self, item_id, field, lang='en_US'):
        ''' return field in italian and job in english
        '''        
        # Readability:
        cr = self.cr
        uid = self.uid
        context = {'lang': lang, }
       
        # Pool used:
        product_pool = self.pool.get('product.product')        
        item_proxy = product_pool.browse(cr, uid, item_id, context=context)
        return item_proxy.__getattribute__(field)

    def get_label_list(self, o, data=None):
        ''' List of all labels for reporting
        '''
        # Readabiliy
        cr = self.cr
        uid = self.uid
        context = {}

        # Pool used:
        mrp_pool = self.pool.get('mrp.production')
        label_pool = self.pool.get('label.label.job')

        res = []
        
        jobs = o.label_job_ids
        placeholder = mrp_pool.get_placeholder_label(
            cr, uid, jobs, context=context)
            
        for job in jobs:
            if job.id in placeholder:            
                (quantity, level) = placeholder[job.id]

                # Extend for address partner break level                
                if level[1] == 'code': 
                    partner = ''
                    address = ''
                else: # partner / address break level
                    partner = level[2].name or ''
                    address = level[3].name if level[3] else ''
                    
                res.append((
                    job, # job data
                    partner, # customization
                    address, # customization
                    #level, # label level
                    quantity, # q.
                    ))
        return res 

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
