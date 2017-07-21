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
import xlrd
import xlsxwriter
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

class ResPartnerProductParticLabel(orm.Model):
    """ Model name: ResPartnerProductParticLabel
    """
    # TODO remove:    
    _name = 'res.partner.product.partic.label'
    _description = 'Label partic'
    
    _columns = {
        'name': fields.selection([        
            ('frame', 'Frame'),
            ('fabric', 'Fabric'),
            #('color', 'Color'), # TODO ???
            ('static_text1', 'Text 1'),
            ('static_text2', 'Text 2'),
            ('static_text3', 'Text 3'),
            ], 'Field', required=True),
        'value': fields.text(
            'Value', required=True) , 
        'partic_id': fields.many2one('res.partner.product.partic', 'Partic'),    
        }        
    
class ResPartnerProductPartic(orm.Model):
    ''' Add product partic obj
    '''    
    _inherit = 'res.partner.product.partic'
    
    _columns = {
        # Customer code:
        'ean13': fields.char('EAN 13', size=13),
        'ean13_mono': fields.char('EAN 13 single', size=13),
        'ean8': fields.char('EAN 8', size=8),
        'ean8_mono': fields.char('EAN 8 single', size=8),
        'partner_pricelist': fields.float('Partner pricelist', digits=(16, 3)), 

        'frame': fields.char('Frame', size=30),# translate=True),
        'fabric_color': fields.char('Fabric color', size=30),#, translate=True),
        'text1': fields.text('Text 1'),#translate=True),
        'text2': fields.text('Text 2'),#, translate=True),
        'text3': fields.text('Text 3'),#, translate=True),
        
        # TODO remove:  
        # Image fields:
        'label_field_ids': fields.one2many(
            'res.partner.product.partic.label', 'partic_id', 
            'Label field'),
        }

class NoteImage(orm.Model):
    ''' Add product partic obj
    '''    
    _inherit = 'note.image'
    
    _columns = {
        'label_image': fields.boolean('Image for label'),
        'label_code': fields.char('Label code', size=15,
            help='Code used for refer image in ODT files'),
        }
        
    _sql_constraints = [(
        'label_code_uniq', 'unique(label_code)', 
        'The label code must be unique!'), 
        ]

class ResPartner(orm.Model):
    ''' Add product partic obj
    '''    
    _inherit = 'res.partner'
    
    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def clean_ascii(self, value):
        ''' Clean no ascii char
        '''
        res = ''
        special = '._- '
        for c in value:
            if c.isalnum() or c in special:
                res += c
            else:
                res += '_'    
        return res
        
    def write_xls_file(self, line):
        ''' Write line in excel file, use self parameter for get WS and row
        '''
        col = 0
        for item in line:
            self.WS.write(self.row, col, item)
            col += 1
        self.row += 1
        return
    
    # -------------------------------------------------------------------------
    # Button:
    # -------------------------------------------------------------------------
    def export_partic_xls_file(self, cr, uid, ids, context=None): 
        ''' Export in XLS for content partic for partner
        '''
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        path = '/home/administrator/photo/xls/partic' # TODO custom value!
        
        # Get filename:
        if current_proxy.label_partic_file:
            filename = current_proxy.label_partic_file
        else:
            filename = '%s.%s.xls' % (
                self.clean_ascii(current_proxy.name),
                current_proxy.id,
                )
            self.write(cr, uid, ids, {
                'label_partic_file': filename,
                }, context=context)    
        
        filename = os.path.join(os.path.expanduser(path), filename)
        _logger.info('Export XLS file: %s' % filename)
                
        WB = xlsxwriter.Workbook(filename)
        self.WS = WB.add_worksheet('Particolarita')
        self.row = 0
        
        # Write header fields:
        extra_pool = self.pool.get('res.partner.product.partic.label')
        # Partic field:
        header = [
            #'ID',
            'default_code',
            'partner_pricelist',
            'partner_code',
            'partner_description',
            'ean8',
            'ean8_mono',
            'ean13',
            'ean13_mono',
            ]

        # Extra data:    
        extra_fields = [f[0] for f in extra_pool._columns['name'].selection]
        header.extend(extra_fields) # selection elements        
        self.write_xls_file(header)    
        
        # Write data row:
        for partic in current_proxy.partic_ids:        
            # Partic field:
            partic_row = [
                #partic.id,
                partic.product_id.default_code or '',
                partic.partner_pricelist or 0.0,
                partic.partner_code or '',
                partic.partner_description or '',
                partic.ean8 or '', 
                partic.ean8_mono or '', 
                partic.ean13 or '',
                partic.ean13_mono or '',
                
                # Extra data:
                partic.frame or '',
                partic.fabric_color or '',
                partic.text1 or '',
                partic.text2 or '',
                partic.text3 or '',                
                ]
                
            self.write_xls_file(partic_row)    

        _logger.info('End export XLS file: %s' % filename)                
        return True

    def import_partic_xls_file(self, cr, uid, ids, context=None): 
        ''' Import in XLS for content partic for partner
        '''
        def format_ean(value, mode=13):
            ''' Format EAN importing from excel
            '''
            if not value:
                return ''
            mask = '%%0%dd' % mode
            
            str_value = str(value)
            if len(str_value) == mode - 1: # no last char
                import barcode
                ean_class = 'ean%s' % mode
                EAN = barcode.get_barcode_class(ean_class)
                ean = EAN(str_value)
                value = ean.get_fullcode() # override ean code                
            try:
                return mask % int(value)
            except:
                _logger.error('Error convert value EAN: %s' % value)
                
        def format_float(value):
           ''' Format fload from xls file
           '''
           if not value:
               return 0.0
           return float(value)
           
        # Pool used
        partic_pool = self.pool.get('res.partner.product.partic')
        product_pool = self.pool.get('product.product')
        
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        path = '/home/administrator/photo/xls/partic' # TODO custom value!
        max_line = 100000
        
        # Get filename:
        if not current_proxy.label_partic_file:
            raise osv.except_osv(
                _('Filename error'), 
                _('No file name for import XLS partic'),
                )

        filename = current_proxy.label_partic_file
        
        filename = os.path.join(os.path.expanduser(path), filename)
        _logger.info('Import XLS file: %s' % filename)

        try:                
            WB = xlrd.open_workbook(filename)
            WS = WB.sheet_by_index(0)
        except:
            raise osv.except_osv(
                _('Open file error'), 
                _('Cannot found file: %s [%s]' % (filename, sys.exc_info())),
                )  

        # Read partic yet present:
        partic_present = {} # DB for code yet present
        for partic in current_proxy.partic_ids: 
            partic_present[partic.product_id.default_code] = partic.id
            
        header = False
        for i in range(0, max_line):
            try:
                if i == 0:
                    header = WS.row(i)
                    continue
                else:
                    row = WS.row(i)
            except:
                # Out of range error ends import:
                _logger.warning('Read end at line: %s' % i)
                break
                    
            # Parse line:
            default_code = row[0].value
            if not default_code:
                _logger.error('Code not found in line: %s' % i)
                continue
               
            data = {
                'partner_id': current_proxy.id,
                #'product_id': product_id
                
                # Field to import:    
                'partner_pricelist': format_float(row[1].value),
                'partner_code': row[2].value or '',
                'partner_description': row[3].value or '',
                'ean8': format_ean(row[4].value, 8),
                'ean8_mono': format_ean(row[5].value, 8),
                'ean13': '%s' % format_ean(row[6].value),
                'ean13_mono': '%s' % format_ean(row[7].value),
                
                # Parametrize for extra:
                'frame': row[8].value or '',
                'fabric_color': row[9].value or '',
                'text1': row[10].value or '',
                'text2': row[11].value or '',
                'text3': row[12].value or '',
                }

            partic_id = partic_present.get(default_code, False)
            if partic_id:
                item_id = partic_present[default_code]
                partic_pool.write(cr, uid, partic_id, data, context=context)
                
            else:
                product_ids = product_pool.search(cr, uid, [
                    ('default_code', '=', default_code)], context=context)
                if not product_ids:
                    _logger.error('New product not present: %s' % default_code)
                    continue    
                    
                data['product_id'] = product_ids[0]
                partic_pool.create(cr, uid, data, context=context)
                                    
        _logger.info('End import XLS file: %s' % filename)                
        return True
        
    def get_tri_state(self, cr, uid, context=None):
        return [ 
            ('show', 'Show'), # ON
            ('hide', 'Hide'), # OFF 
            #('not', 'Not selected'), # NOT PRESENT
            ]
    
    def get_partic_partner_product_label(self, cr, uid, product_id, partner_id, 
            address_id=False, context=None):
        ''' Get partner product partic information
        '''
        partic_pool = self.pool.get('res.partner.product.partic')        
        res = False
        if address_id:
            res = partic_pool.search(cr, uid, [
                ('partner_id.has_custom_label', '=', True),
                ('partner_id', '=', address_id),
                ('product_id', '=', product_id),
                ], context=context)
                
        if not res: # no address or no partic for address        
            res = partic_pool.search(cr, uid, [
                ('partner_id.has_custom_label', '=', True),
                ('partner_id', '=', partner_id),
                ('product_id', '=', product_id),
                ], context=context)
                
        # TODO check double        
        if res:
            return partic_pool.browse(cr, uid, res, context=context)[0]
        else:
            return False    
    
    def get_translate_description_data(self, cr, uid, product, field, langs,
            separator='\n', context=None):
        ''' Load description for product translateble field
            product: proxy obj
            field: field name
            langs: text database for extra lang
            separator: from one field to another
            context: dictionary
        '''        
        check_lang = {
            'en': 'en_US', 
            'fr': 'fr_FR',
            } # TODO better!
        
        if context is None:
            context = {}
        product_pool = self.pool.get('product.product')
        
        res = product.__getattribute__(field) or '' # default language
        if not langs:
            return res
            
        ctx = context.copy()
        for lang in langs.split('|'):
            lang_db = lang.lower()
            if lang_db not in check_lang:   
                _logger.error('Lang format not present: %s' % lang)
                continue
            ctx['lang'] = check_lang[lang_db]
            product_lang = product_pool.browse(
                cr, uid, product.id, context=ctx)
            res += '%s%s' % (
                separator, 
                product_lang.__getattribute__(field) or '')
        return res  

    def generate_job_data_from_line_partner(self, cr, uid, **parameter):
        ''' Generate record for create printing jobs
            Parameter >> Dict for not mandatory paremeters, list below:
            
            line: used for generate all parameter, instead read passed (*_id)
            product_id: ID of product
            partner_id: ID of partner
            address_id: ID of address
            order_id: ID of order
            mrp_id: ID of MRP
            context: dict of extra parameter
        '''
        # ---------------------------------------------------------------------
        # UTILITY FUNCTION:
        # ---------------------------------------------------------------------            
        def get_label(company, partner, address, field):
            ''' Check field from address, partner, company return first found
            '''       
            res = '' 
            if address and address.has_custom_label: # address
                res = address.__getattribute__(field) or ''
            if not res and partner.has_custom_label: # partner
                res = partner.__getattribute__(field) or ''
            if not res: # company
                res = company.partner_id.__getattribute__(field) or ''
            if not res: # not res (Not an error TODO raise?):
                _logger.warning('Warning %s not found string value!' % field)            
            return res

        def get_state_value(company, partner, address, field, warning=False):
            ''' Check field from address, partner, company return state value
                as True or False
            '''
            res = ''
            if address and address.has_custom_label: # address
                res = address.__getattribute__(field) or ''
            if not res and partner.has_custom_label: # partner
                res = partner.__getattribute__(field) or ''
            if not res: # company
                res = company.partner_id.__getattribute__(field) or ''
            if warning and not res:
                _logger.warning('Field %s not set up as show or hide!' % field) 

            if res == 'show':
                return True
            else:
                return False        
            
        # ---------------------------------------------------------------------
        # Read parameters:
        # ---------------------------------------------------------------------
        context = parameter.get('context', {})
        line = parameter.get('line', False)
        
        # Pool used:
        product_pool = self.pool.get('product.product')
        partner_pool = self.pool.get('res.partner') # and also address
        order_pool = self.pool.get('sale.order')
        mrp_pool = self.pool.get('mrp.production')
        
        # ---------------------------------------------------------------------
        # Header many2one data:
        # ---------------------------------------------------------------------
        if line:
            # Create browse obj for readability:
            product = line.product_id # TODO lang?
            partner = line.order_id.partner_id
            address = line.order_id.destination_partner_id
            order = line.order_id
            mrp = line.mrp_id
            deadline = line.date_deadline or order.date_deadline or ''

            # Create record of m2o                
            record = {
                'product_id': product.id,
                'partner_id': partner.id,
                'address_id': address.id,
                'order_id': order.id,
                'line_id': line.id,
                'mrp_id': mrp.id,
                }
        else:
            # Get ID from parameters:
            product_id = parameter.get('product_id', False)
            partner_id = parameter.get('partner_id', False)
            address_id = parameter.get('address_id', False)
            order_id = parameter.get('order_id', False)
            mrp_id = parameter.get('mrp_id', False)
            deadline = order_id.order_deadline or ''
            
            # Check mandatory ID (else no data for label)
            if product_id:
                product = product_pool.browse(
                    cr, uid, product_id, context=context)
            else: # Mandatory element, raise error
                raise osv.except_osv(
                    _('No data'), 
                    _('Product ref. not present'),
                    )                
            if partner_id:
                partner = partner_pool.browse(
                    cr, uid, partner_id, context=context)
            else: # Mandatory element, raise error
                raise osv.except_osv(
                    _('No data'), 
                    _('Partner ref. not present'),
                    )
            if address_id:
                address = partner_pool.browse(
                    cr, uid, address_id, context=context)
            else:
                address = False # not mandatory
            if order_id:
                order = order_pool.browse(
                    cr, uid, order_id, context=context)
            else: # Mandatory element, raise error
                raise osv.except_osv(
                    _('No data'), 
                    _('Order ref. not present'),
                    )
            if mrp_id:
                mrp = mrp_pool.browse(
                    cr, uid, mrp_id, context=context)
            else: # Mandatory element, raise error
                raise osv.except_osv(
                    _('No data'), 
                    _('MRP ref. not present'),
                    )

            # Create record of m2o                
            record = {
                'product_id': product_id,
                'partner_id': partner_id,
                'address_id': address_id,
                'order_id': order_id,
                'line_id': False,
                'mrp_id': mrp_id,
                }

        company = partner.company_id # Common reference

        # ---------------------------------------------------------------------
        # Check parameter in partner address form:
        # ---------------------------------------------------------------------
        # Check and label string from address or partner setup:
        record.update({            
            # -----------------------------------------------------------------
            # Extra data:
            # -----------------------------------------------------------------
            'has_partner_custom': partner.has_custom_label or False,
            'has_address_custom': address.has_custom_label or False,
        
            # -----------------------------------------------------------------
            # String label:
            # -----------------------------------------------------------------
            # Anagrafic text:
            'record_string_code': get_label(
                company, partner, address, 
                'label_string_code'),
            'record_string_code_partner': get_label(
                company, partner, address, 
                'label_string_code_partner'),
            'record_string_description': get_label(
                company, partner, address, 
                'label_string_description'),
            'record_string_description_partner': get_label(
                company, partner, address, 
                'label_string_description_partner'),
            'record_string_frame': get_label(
                company, partner, address, 
                'label_string_frame'),
            'record_string_fabric': get_label(
                company, partner, address, 
                'label_string_fabric'),

            # Anagrafic numeric:
            'record_string_q_x_pack': get_label(
                company, partner, address, 
                'label_string_q_x_pack'),
            'record_string_q_x_pallet': get_label(
                company, partner, address, 
                'label_string_q_x_pallet'),
            'record_string_dimension': get_label(
                company, partner, address, 
                'label_string_dimension'),
            'record_string_volume': get_label(
                company, partner, address, 
                'label_string_volume'),
            'record_string_weight_net': get_label(
                company, partner, address, 
                'label_string_weight_net'),
            'record_string_weight_lord': get_label(
                company, partner, address, 
                'label_string_weight_lord'),
            'record_string_parcel': get_label(
                company, partner, address, 
                'label_string_parcel'),
            'record_string_price': get_label(
                company, partner, address, 
                'label_string_price'),
            
            # EAN (no label):
            
            # Production:
            'record_string_line': get_label(
                company, partner, address, 
                'label_string_line'),
            'record_string_period': get_label(
                company, partner, address, 
                'label_string_period'), 
            'record_string_lot': get_label(
                company, partner, address, 
                'label_string_lot'),
                
            # Order:
            'record_string_order_ref': get_label(
                company, partner, address, 
                'label_string_order_ref'), 
            'record_string_order_date': get_label(
                company, partner, address, 
                'label_string_order_date'), 
            'record_string_order_deadline': get_label(
                company, partner, address, 
                'label_string_order_deadline'), 
            'record_string_destination_code': get_label(
                company, partner, address, 
                'label_string_destination_code'), 
            
            # Image (no label):
            
            # Counter:
            'record_string_counter_pack_total': get_label(
                company, partner, address, 
                'label_string_counter_pack_total'),  

            # -----------------------------------------------------------------
            # Hide Show check for label (form partner tri-state):
            # -----------------------------------------------------------------
            # Anagrafic text:
            'record_print_code': get_state_value(
                company, partner, address, 
                'label_print_code'),
            'record_print_code_partner': get_state_value(
                company, partner, address, 
                'label_print_code_partner'),
            'record_print_description': get_state_value(
                company, partner, address, 
                'label_print_description'), 
            'record_print_description_partner': get_state_value(
                company, partner, address, 
                'label_print_description_partner'), 
            'record_print_frame': get_state_value(
                company, partner, address, 
                'label_print_frame'),
            'record_print_fabric': get_state_value(
                company, partner, address, 
                'label_print_fabric'),

            # Anagrafic numeric:
            'record_print_q_x_pack': get_state_value(
                company, partner, address, 
                'label_print_q_x_pack'), 
            'record_print_q_x_pallet': get_state_value(
                company, partner, address, 
                'label_print_q_x_pallet'), 
            'record_print_dimension': get_state_value(
                company, partner, address, 
                'label_print_dimension'), 
            'record_print_volume': get_state_value(
                company, partner, address, 
                'label_print_volume'), 
            'record_print_weight_net': get_state_value(
                company, partner, address, 
                'label_print_weight_net'), 
            'record_print_weight_lord': get_state_value(
                company, partner, address, 
                'label_print_weight_lord'),
            'record_print_parcel': get_state_value(
                company, partner, address, 
                'label_print_parcel'), 
            'record_print_price': get_state_value(
                company, partner, address, 
                'label_print_price'), 
            'record_print_price_uom': get_state_value(
                company, partner, address, 
                'label_print_price_uom'),

            # EAN data:
            'record_print_ean13': get_state_value(
                company, partner, address, 
                'label_print_ean13'), 
            'record_print_ean8': get_state_value(
                company, partner, address, 
                'label_print_ean8'), 
            
            # Production:
            'record_print_line': get_state_value(
                company, partner, address, 
                'label_print_line'),
            'record_print_period': get_state_value(
                company, partner, address, 
                'label_print_period'),
            'record_print_lot': get_state_value(
                company, partner, address, 
                'label_print_lot'), 
            
            # Order:
            'record_print_order_ref': get_state_value(
                company, partner, address, 
                'label_print_order_ref'),
            'record_print_order_date': get_state_value(
                company, partner, address, 
                'label_print_order_date'),
            'record_print_order_deadline': get_state_value(
                company, partner, address, 
                'label_print_order_deadline'),
            'record_print_destination_code': get_state_value(
                company, partner, address, 
                'label_print_destination_code'),
                
            # Image:
            'record_print_company_logo': get_state_value(
                company, partner, address, 
                'label_print_company_logo'), 
            'record_print_partner_logo': get_state_value(
                company, partner, address, 
                'label_print_partner_logo'), 
            'record_print_linedrawing': get_state_value(
                company, partner, address, 
                'label_print_linedrawing'), 
            #'label_print_product_image': 
            
            # Counter:            
            'record_print_counter_pack_total': get_state_value(
                company, partner, address, 
                'label_print_counter_pack_total'),           
            })               
        
        # ---------------------------------------------------------------------
        # Get information for merge language fields:
        # ---------------------------------------------------------------------
        merge_lang = {
            'description': get_label(
                company, partner, address, 'label_lang_description'),
            'frame': get_label(
                company, partner, address, 'label_lang_frame'),
            'fabric': get_label(
                company, partner, address, 'label_lang_fabric')             
            }
            
        # ---------------------------------------------------------------------
        # Product, MRP, Order data fields:
        # ---------------------------------------------------------------------
        # Get complex field:
        try:
            line_code = mrp.lavoration_ids[0].workcenter_id.code
        except:
            _logger.error('No line!')
            line_code = ''
        
        # ---------------------------------------------------------------------
        # Partic update:
        # ---------------------------------------------------------------------
        separator = '-' #'\n' # for pack TODO - for article?
        # Update record with data:  

        if partner.has_custom_label or address.has_custom_label:
            product_partic = self.get_partic_partner_product_label(
                cr, uid, product.id, partner.id, 
                address.id if address else False, context=context)
        else:
            product_partic = False

        # Company partner parent (linked for get secondary code)        
        if company.partner_id.partic_partner_code_id:
            # Now used only for partner extra code if not present
            company_product_partic = self.get_partic_partner_product_label(
                cr, uid, product.id, 
                company.partner_id.partic_partner_code_id.id, False, 
                context=context)
        else:
            company_product_partic = False
            
        # Force partner product description:

        # ---------------------------------------------------------------------
        # Translated fields append:
        # ---------------------------------------------------------------------        
        description = self.get_translate_description_data(
            cr, uid, product, 'name', merge_lang['description'],
            separator=separator, context=context)

        frame = self.get_translate_description_data(
            cr, uid, product, 'label_frame', merge_lang['frame'],
            separator=separator, context=context)
        fabric_color = self.get_translate_description_data(
            cr, uid, product, 'label_fabric_color', merge_lang['fabric'],
            separator=separator, context=context)
        
        # Depend on check q_x_pack:
        ean13 = product.ean13 or ''
        ean8 = product.ean8 or ''
        # Check mono label:
        (ean13_mono, ean8_mono) = product_pool.get_ean_mono(  
            cr, uid, product.default_code, context=context)
        # Priority to force in anagraphic
        ean13_mono = product.ean13_mono or ean13_mono
        ean8_mono = product.ean8_mono or ean8_mono
        
        if product_partic:
            frame = product_partic.frame or frame or ''
            fabric_color = product_partic.fabric_color or fabric_color or ''
            partner_code = product_partic.partner_code or ''
            partner_description = product_partic.partner_description or ''
            ean13 = product_partic.ean13 or ean13 or ''
            ean13_mono = product_partic.ean13_mono or ean13_mono or ''
            ean8 = product_partic.ean8 or ean8 or ''
            ean8_mono = product_partic.ean8_mono or ean8_mono or ''
            text1 = product_partic.text1
            text2 = product_partic.text2
            text3 = product_partic.text3
        else: # else nothing
            partner_code = ''
            partner_description = ''
            text1 = ''
            text2 = ''
            text3 = ''
                    
        # Force if not present partner_code
        if company_product_partic:
            partner_code = \
                partner_code or company_product_partic.partner_code or ''
            
        record.update({
            # -----------------------------------------------------------------
            #                               PRODUCT:
            # -----------------------------------------------------------------
            'record_data_code': product.default_code,
            'record_data_code_partner': partner_code,
            'record_data_description': description,
            'record_data_description_partner': partner_description,
                
            'record_data_frame': frame,
            'record_data_fabric': fabric_color,

            # Anagrafic numeric:        
            # TODO change float
            'record_data_q_x_pack': 
                int(product.q_x_pack) if product.q_x_pack else '',
            'record_data_q_x_pallet': product.q_x_pallet or '',
            'record_data_dimension': '%sx%sx%s' % (
                product.height, product.width, product.length) if (
                    product.height and product.width and product.length) else\
                        '',
            'record_data_volume': product.volume,
            'record_data_weight_net': product.weight_net,
            'record_data_weight_lord': product.weight,
            'record_data_parcel': 'TODO' or product.parcel,
            'record_data_price': product.lst_price, # TODO
            'record_data_price_uom': product.uom_id.name,

            # EAN data:
            'record_data_ean13': ean13,
            'record_data_ean13_mono': ean13_mono,
            'record_data_ean8': ean8,
            'record_data_ean8_mono': ean8_mono,
            # TODO single
            
            # -----------------------------------------------------------------
            #                                MRP:
            # -----------------------------------------------------------------
            'record_data_line': line_code,
            #'record_data_period': '%s%s' % (
            #    mrp.date_planned[2:4], mrp.date_planned[5:7]),
            # TODO format YY WW
            'record_data_period': '%s%02d' % (
                mrp.date_planned[2:4],
                datetime.strptime(
                    mrp.date_planned[:10], 
                    DEFAULT_SERVER_DATE_FORMAT,
                    ).isocalendar()[1]),
            'record_data_lot': mrp.name.replace('MO', '').lstrip('0'),
            
            # -----------------------------------------------------------------
            #                               ORDER:
            # -----------------------------------------------------------------
            'record_data_order_ref': order.client_order_ref or '', #label_order
            'record_data_order_date': order.date_order[:10],
            'record_data_order_deadline': deadline, # 2 case (at begin of proc)
            'record_data_destination_code': 
                order.destination_partner_id.label_destination_code\
                    if order.destination_partner_id else '', # XXX only address
                
            # -----------------------------------------------------------------
            #                               IMAGES:
            # -----------------------------------------------------------------
            # Image:
            # XXX Note: used related elements
            #record_data_company_logo 
            #'record_data_partner_logo': order.company_id.partner_id.label_logo,
            #record_data_linedrawing label_print_product_image        
            
            # Extra images:
            # XXX Note: used related elements
            #record_data_extra_image_ids
            
            # -----------------------------------------------------------------
            #                            STATIC TEXT:
            # -----------------------------------------------------------------
            'record_data_text1': text1,
            'record_data_text2': text2,
            'record_data_text3': text3,
            })
            
        return record        

    _columns = { 
        # Data for label:
        'label_destination_code': fields.char(
            'Label destination code', size=30, 
            help='Partner destination code, used for print in label'),

        # Parameters:
        'has_custom_label': fields.boolean('Has custom label'),
        'has_pallet_label': fields.boolean('Has pallet label'),
        # TODO add here partner ref!
        
        'partic_partner_code_id': fields.many2one(
            'res.partner', 'Partner partic code',
            help='Partner linked for get customer product code in label'),
       
        'label_partic_file': fields.char('Partic import file', size=80,
            help='Used for import export data in partner form'),
                
        # ---------------------------------------------------------------------
        #                      EXTRA LANGUAGE ELEMENTS:
        # ---------------------------------------------------------------------
        #'label_lang_code': fields.char(
        #    'Print company code', 
        #    size=40, help='Extra lang code, use format: EN|DE|FR|IT'),
        'label_lang_description': fields.char(
            'Lang for description', 
            size=40, help='Extra lang descrition, use format: EN|DE|FR|IT'),
        'label_lang_frame': fields.char('Lang for frame',
            size=40, help='Extra lang frame, use format: EN|DE|FR|IT'),
        'label_lang_fabric': fields.char('Label for fabric', 
            size=40, help='Extra lang fabric, use format: EN|DE|FR|IT'), 
        #'label_lang_color': fields.char('Lang for color', 
        #    size=40, help='Extra lang code, use format: EN|DE|FR|IT'), 

        # ---------------------------------------------------------------------
        #                      LABEL STRING FOR ALL ELEMENTS:
        # ---------------------------------------------------------------------
        # Anagrafic text:
        'label_string_code': fields.char(
            'String company code', 
            size=40, translate=True),
        'label_string_code_partner': fields.char('String partner code', 
            size=40, translate=True),
        'label_string_description': fields.char(
            'String company description', 
            size=40, translate=True),
        'label_string_description_partner': fields.char(
            'String partner description', 
            size=40, translate=True),
        'label_string_frame': fields.char('String frame',
            size=40, translate=True),
        'label_string_fabric': fields.char('String fabric', 
            size=40, translate=True),

        # Anagrafic numeric:        
        'label_string_q_x_pack': fields.char('String Q. x pack', 
            size=40, translate=True),
        'label_string_q_x_pallet': fields.char('String Q. x pallet', 
            size=40, translate=True),
        'label_string_dimension': fields.char('String dimension', 
            size=40, translate=True),
        'label_string_volume': fields.char('String volume', 
            size=40, translate=True),
        'label_string_weight_net': fields.char('String weight net', 
            size=40, translate=True),
        'label_string_weight_lord': fields.char('String weight lord', 
            size=40, translate=True),
        'label_string_parcel': fields.char('String parcel', 
            size=40, translate=True),
        'label_string_price': fields.char('String price', 
            size=40, translate=True),
        #'label_string_price_uom':

        # EAN data:
        #'label_string_ean13' 'label_string_ean8'
        
        # Production:
        'label_string_line': fields.char('String production line', 
            size=40, translate=True, help='Line code in database'),
        'label_string_period': fields.char('String period', 
            size=40, translate=True, help='YYMM of production'),
        'label_string_lot': fields.char('String lot', 
            size=40, translate=True, help='MRP number'),
        
        # Order:
        'label_string_order_ref': fields.char('String order ref', 
            size=40, translate=True), # customer
        'label_string_order_date': fields.char('String order date', 
            size=40, translate=True),
        'label_string_order_deadline': fields.char('String order deadline', 
            size=40, translate=True),
        'label_string_destination_code': fields.char(
            'String destination code', 
            size=40, translate=True),
            
        # Image:
        #'label_string_company_logo' 'label_string_partner_logo'
        #'label_string_linedrawing' 'label_string_product_image'
               
        # Counter:            
        'label_string_counter_pack_total': fields.char('String counter pack', 
            size=40, translate=True),   

        # ---------------------------------------------------------------------
        #               SHOW HIDE ELEMENT IN REPORT DEPEND ON PARTNER:
        # ---------------------------------------------------------------------
        # XXX Note: element are in 3-state for parent required selection!
        
        # Anagrafic text:
        'label_print_code': fields.selection(get_tri_state, 
            'Print company code'),
        'label_print_code_partner': fields.selection(get_tri_state, 
            'Print partner code'),
        'label_print_description': fields.selection(get_tri_state, 
            'Print company description'),
        'label_print_description_partner': fields.selection(get_tri_state, 
            'Print partner description'),
        'label_print_frame': fields.selection(get_tri_state, 
            'Print frame'),
        'label_print_fabric': fields.selection(get_tri_state, 
            'Print fabric'),

        # Anagrafic numeric:        
        'label_print_q_x_pack': fields.selection(get_tri_state, 
            'Print Q. x pack'),
        'label_print_q_x_pallet': fields.selection(get_tri_state, 
            'Print Q. x pallet'),
        'label_print_dimension': fields.selection(get_tri_state, 
            'Print dimension'),
        'label_print_volume': fields.selection(get_tri_state, 
            'Print volume'),
        'label_print_weight_net': fields.selection(get_tri_state, 
            'Print weight net'),
        'label_print_weight_lord': fields.selection(get_tri_state, 
            'Print weight lord'),
        'label_print_parcel': fields.selection(get_tri_state, 
            'Print parcel'),
        'label_print_price': fields.selection(get_tri_state, 
            'Print price'),
        'label_print_price_uom': fields.selection(get_tri_state, 
            'Print price uom'), # TODO add

        # EAN data:
        'label_print_ean13': fields.selection(get_tri_state, 
            'Print EAN13'),
        'label_print_ean8': fields.selection(get_tri_state, 
            'Print EAN8'),
        
        # Production:
        'label_print_line': fields.selection(get_tri_state, 
            'Print production line'),
        'label_print_period': fields.selection(get_tri_state, 
            'Print period',
            help='Production period YYMM  format es.: 1601'),
        'label_print_lot': fields.selection(get_tri_state, 
            'Print lot'),
        
        # Order:
        'label_print_order_ref': fields.selection(get_tri_state, 
            'Print order ref'), # customer
        'label_print_order_date': fields.selection(get_tri_state, 
            'Print order date'),
        'label_print_order_deadline': fields.selection(get_tri_state, 
            'Print order deadline'),
        'label_print_destination_code': fields.selection(get_tri_state,             
            'Print destination code'),
            
        # Image:
        'label_print_company_logo': fields.selection(get_tri_state, 
            'Print company logo'),
        'label_print_partner_logo': fields.selection(get_tri_state, 
            'Print partner logo'),
        'label_print_linedrawing': fields.selection(get_tri_state, 
            'Print line drawing'),
        #'label_print_product_image': fields.selection(get_tri_state, 
        #    'Print product mage'), # TODO add what album
        
        # Extra images:
        'label_print_extra_image_ids': fields.many2many(
            'note.image', 'note_image_label_rel', 
            'label_id', 'image_id', 
            'Extra image'),
               
        # Counter:            
        'label_print_counter_pack_total': fields.selection(get_tri_state, 
            'Print counter pack',
            help='For print in label: 1/25, 2/25... (reset every product)'),   
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
