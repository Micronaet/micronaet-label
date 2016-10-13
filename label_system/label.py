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

    _name = 'label.layout'
    _description = 'Label layout'

    _columns = {    
        'code': fields.char('Code', size=12), 
        'name': fields.char('Label format', size=64, required=True), 
        'note': fields.text('Note'),
        'continue': fields.boolean('Continue format'),
        
        # Dimension:
        'height': fields.float('Height', help='Height of label in mm.'),
        'width': fields.float('Width', help='Width of label in mm.'),
        
        # Interspace:
        'top': fields.float('Left', help='Top interspace in mm.'),
        'right': fields.float('Left', help='Right interspace in mm.'),
        'left': fields.float('Height', help='Left interspace in mm.'),        

        # Numer of label:
        'total': fields.integer('Total', help='Total label per row'),        
        }    

class LabelLabel(orm.Model):
    """ Model name: LabelLabel
    """

    _name = 'label.label'
    _description = 'Label'

    _columns = {
    
        }
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
        extension = 'odt'
        
        report_pool = self.pool.get('ir.actions.report.xml')
        
        folder_in = os.path.expanduser(self.get_config_base_path(
            cr, uid, 'import', context=context))
        folder_out = os.path.expanduser(self.get_config_base_path(
            cr, uid, 'datastore', context=context))
        for f in os.listdir(folder_in):
            if f[-3:].lower() != extension: 
               continue # jump
               
            # -------------   
            # Create label:
            # -------------   
            label_id = self.create(cr, uid, {
                'name': f[:-4], # file name no ext.
                'description': f[:-4],
                'filename': f,
                # TODO report_id 
                }, context=context)
            f_in = os.path.join(folder_id, f)   
            f_out = os.path.join(folder_out, '%s.%s' % (label_id, extension))
            try:
                os.rename(f_in, f_out)
            except:
                _logger.error('Error import label: %s/%s' % (folder_in, f))
                self.unlink(cr, uid, label_id, context=context)
                continue

            # --------------------
            # Create report aeroo:
            # --------------------
            report_id = report_pool.create(cr, uid, {
                'name': f,
                'type': 'ir.actions.report.xml',
                'model': 'label.label',
                'report_name': 'label_label_report_%s' % label_id,
                'report_type': 'aeroo',
                'in_format': 'oo-odt',
                #'out_format': 'oo-pdf',
                'parse_loc': 'label_system/report/label_parser.py',
                'report_rml': f_out,
                'parse_stat': 'loc',
                'tml_source': 'file',
                }, context=context) 
            '''
            TODO   
            <ir_set>
                <field eval="'action'" name="key"/>
                <field eval="'client_print_multi'" name="key2"/>
                <field eval="['mrp.bom']" name="models"/>
                <field name="name">action_fiam_bom_report_no_cost</field>
                <field eval="'ir.actions.report.xml,'+str(aeroo_fiam_bom_custom_no_cost)" name="value"/>
                <field eval="True" name="isobject"/>
                <field eval="True" name="replace"/>
            </ir_set>
            '''
            # ----------------------------
            # Update information on label:
            # ----------------------------
            self.write(cr, uid, label_id, {
                'report_id': report_id,
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
        'create_date': fields.date('Create date'),
        'code': fields.char('Code', size=12), 
        'name': fields.char('Label', size=64, required=True), 
        'description': fields.text('Description'),

        'filename': fields.char('Filename', size=64, 
            help='original file name'),
        'layout_id': fields.many2one(
            'label.layout', 'Layout format'),
        'report_id': fields.many2one(
            'ir.actions.report.xml', 'Report action'),
        'parser': fields.char('Parser', size=64),

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
