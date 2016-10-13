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

# TODO manage printer for direct report with CUPS?
class LabelLabel(orm.Model):
    """ Model name: LabelLabel
    """

    _name = 'label.label'
    _description = 'Label'

    # -------------------------------------------------------------------------    
    #                            UTILITY:
    # -------------------------------------------------------------------------    
    # Parent management:
    def get_config_base_path(self, cr, uid, mode, context=None):
        ''' Read parameter: 
            mode = 'import' or 'datastore' path
        '''    
        if mode not in ['import', 'datastore']:
            raise osv.except_osv(
                _('Path error!'), 
                _('Path are only datastore or import not %s') % mode)
                
        key = 'label.label.%s.path' % mode
        
        config_pool = self.pool.get('ir.config_parameter')
        config_ids = config_pool.search(cr, uid, [
            ('key', '=', key)], context=context)
        if not config_ids:
            _logger.warning('Parameter not found: %s' % key)
            return []
        config_proxy = config_pool.browse(
            cr, uid, config_ids, context=context)[0]
            
        # Create folder if not present:    
        os.system('mkdir -p %s' % config_proxy.value)     
        return config_proxy.value
    
    # -------------------------------------------------------------------------    
    #                              SCHEDULE EVENT:
    # -------------------------------------------------------------------------    
    # Import label (scheduled)
    def scheduled_import_label_label(self, cr, uid, context=None):
        ''' Import procedure for manage module
        '''
        extension = 'ODT'
        folder_in = self.get_config_base_path(
            cr, uid, 'import', context=context)
        folder_out = self.get_config_base_path(
            cr, uid, 'datastore', context=context)
        for f in os.listdir(folder_in):
            if f[-3:].upper() != extension: 
               continue # jump
               
            # Import label:
            self.create(cr, uid, {
                
                }, context=context)   
        return True

    # -------------------------------------------------------------------------    
    #                               WORKFLOW EVENT:
    # -------------------------------------------------------------------------        
    def label_draft(self, cr, uid, ids, context=None):
        ''' Draft WF
        ''' 
        return self.write(cr, uid, ids, {
            'state': 'draft'}, context=context)
    
    def label_confirmed(self, cr, uid, ids, context=None):
        ''' Confirmed WF
        ''' 
        return self.write(cr, uid, ids, {
            'state': 'confirmed'}, context=context)

    def label_disabled(self, cr, uid, ids, context=None):
        ''' Disabled WF
        ''' 
        return self.write(cr, uid, ids, {
            'state': 'disabled'}, context=context)
        
    # -------------------------------------------------------------------------    
    #                                 ORM:
    # -------------------------------------------------------------------------        
    _columns = {
        'code': fields.char('Code', size=12), 
        'name': fields.char('Label', size=64, required=True), 
        'description': fields.text('Description'),

        'filename': fields.char('Filename', size=64, required=True),
        'parser': fields.char('Parser', size=64),

        'height': fields.float('Height', help='Height of label in mm.'),
        'width': fields.float('Width', help='Width of label in mm.'),

        'type': fields.selection([
            ('article', 'Article'),
            ('package', 'Package'),
            ('pallet', 'Pallet'),
            ('placeholder', 'Placeholder'),
            ], 'Type of label', required=True),
        
        'note': fields.text('Note'),
        
        # WF status:
        'state': fields.selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('disabled', 'Disabled'),
            ], 'State'),
        }
    
    _defaults = {
       'type': lambda *a: 'article',
       'state': lambda *x: 'draft',
       }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
