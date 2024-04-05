# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class SaleRentingUpdatePriceWizard(models.TransientModel):
    _name = 'sale.renting.update.price.wizard'
    _description = 'Sale Renting Update Price'

    name = fields.Char(string='New Pricelist', help='Enter the name of the new price list')
    pricelist_id = fields.Many2one(comodel_name='product.pricelist',
                                   string='Pricelist',
                                   help='Select an existing price list')
    visible_confirm = fields.Boolean(string='Visible Confirm?', default=False)
    update = fields.Selection(selection=[('new', 'New Pricelist'), ('existing', 'Existing Pricelist')],
                              string='Update Pricelist',
                              required=True,
                              default='new')
    based_pricelist_id = fields.Many2one(comodel_name='product.pricelist',
                                         string='Based on Pricelist',
                                         help='Select origin price list')
    percentage = fields.Float('Percentage %')
    rounding_factor = fields.Float(string='Rounding', default=1.0)
    rental_product_ids = fields.One2many(comodel_name='sale.renting.product.wizard',
                                         inverse_name='sale_renting_update_price_id',
                                         string='Rental Products')

    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            pricelist_id = self.env['product.pricelist'].search([('name', '=', self.name)], limit=1)
            if pricelist_id:
                return {'warning': {'title': _('Warning'),
                                    'message': _('There is already a price list with that name!')}}

    @api.onchange('rounding_factor')
    def _onchange_rounding_factor(self):
        if self.rounding_factor < 0.0:
            self.rounding_factor = 0.0
            return {'warning': {'title': _('Warning'), 'message': _('The rounding factor cannot be negative!')}}

    @api.onchange('update')
    def _onchange_update(self):
        if self.update == 'new':
            self.pricelist_id = False
        elif self.update == 'existing':
            self.name = False
        else:
            self.name = False
            self.pricelist = False

    def action_upload_rental_product(self):
        rental_pricing_model = self.env['rental.pricing']
        product_template_model = self.env['product.template']
        self.rental_product_ids = [(6, 0, [])]
        rental_product_ids = []

        if self.based_pricelist_id:
            active_ids = self._context.get('active_ids')
            rental_pricing_ids = rental_pricing_model.search([('pricelist_id', '=', self.based_pricelist_id.id),
                                                              ('product_template_id', 'in', active_ids)])
            if rental_pricing_ids:
                for rental_pricing_id in rental_pricing_ids:
                    vals = {'product_template_id': rental_pricing_id.product_template_id.id,
                            'rental_pricing_id': rental_pricing_id.id,
                            'duration': rental_pricing_id.duration,
                            'unit': rental_pricing_id.unit,
                            'currency_id': rental_pricing_id.currency_id.id,
                            'actual_price': rental_pricing_id.price,
                            'new_price': 0.0}

                    rental_product_ids.append((0, 0, vals))
            else:
                raise UserError(_('There are no rental products for the chosen base list!'))
        else:
            product_template_ids = product_template_model.search([('rent_ok', '=', True)])
            if product_template_ids:
                for product_template_id in product_template_ids:
                    vals= {'product_template_id': product_template_id.id,
                           'rental_pricing_id': False,
                           'currency_id': self.env.company.currency_id.id,
                           'duration': 1,
                           'unit': 'day',
                           'actual_price': 0.0,
                           'new_price': 0.0}

                    rental_product_ids.append((0, 0, vals))

        self.rental_product_ids = rental_product_ids

        return {'type': 'ir.actions.act_window',
                'res_model': 'sale.renting.update.price.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new'}

    def action_update_rental_price(self):
        self.visible_confirm = True
        update_factor = 1 + (self.percentage / 100)
        for rental_product_id in self.rental_product_ids:
            if rental_product_id.actual_price > 0.0:
                new_price = rental_product_id.actual_price * update_factor
                rental_product_id.new_price = tools.float_round(new_price, precision_rounding=self.rounding_factor)

        return {'type': 'ir.actions.act_window',
                'res_model': 'sale.renting.update.price.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new'}

    def action_confirm(self):
        if self.rental_product_ids:
            rental_pricing_model = self.env['rental.pricing']
            if self.pricelist_id:
                for rental_product_id in self.rental_product_ids:
                    if rental_product_id.new_price > 0.0:
                        if self.pricelist_id == rental_product_id.rental_pricing_id.pricelist_id:
                            rental_product_id.rental_pricing_id.write({'price': rental_product_id.new_price})
                        else:
                            rental_pricing_model.create({'product_template_id': rental_product_id.product_template_id,
                                                         'duration': rental_product_id.duration,
                                                         'unit': rental_product_id.unit,
                                                         'currency_id': rental_product_id.currency_id.id,
                                                         'pricelist_id': self.pricelist_id.id,
                                                         'price': rental_product_id.new_price})
            else:
                new_pricelist_id = self.env['product.pricelist'].create({'name': self.name})
                for rental_product_id in self.rental_product_ids:
                    if rental_product_id.new_price > 0.0:
                        rental_pricing_model.create({'product_template_id': rental_product_id.product_template_id.id,
                                                     'duration': rental_product_id.duration,
                                                     'unit': rental_product_id.unit,
                                                     'currency_id': rental_product_id.currency_id.id,
                                                     'pricelist_id': new_pricelist_id.id,
                                                     'price': rental_product_id.new_price})


class SaleRentingProductWizard(models.TransientModel):
    _name = 'sale.renting.product.wizard'
    _description = 'Sale Renting Products'

    sale_renting_update_price_id = fields.Many2one(comodel_name='sale.renting.update.price.wizard',
                                                   string='Rental Update Price Wizard')
    product_template_id = fields.Many2one(comodel_name='product.template', string='Product Template')
    rental_pricing_id = fields.Many2one(comodel_name='rental.pricing', string='Rental Pricing')
    name = fields.Char(related='product_template_id.name', string='Rental Product')
    duration = fields.Integer(string="Duration")
    unit = fields.Selection(selection=[("hour", "Hours"), ("day", "Days"), ("week", "Weeks"), ("month", "Months")],
                            string="Unit", default='day')
    currency_id = fields.Many2one(comodel_name='res.currency',
                                  string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
    product_variant_ids = fields.Many2many(comodel_name='product.product',
                                           string="Product Variants")
    actual_price = fields.Float('Actual Price')
    new_price = fields.Float('New Price')
