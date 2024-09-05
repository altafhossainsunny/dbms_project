from flask import Blueprint, render_template, flash, send_from_directory, redirect
from flask_login import login_required, current_user
from .forms import ShopItemsForm, OrderForm
from werkzeug.utils import secure_filename
from .models import Product, Order, Customer
from . import db
from sqlalchemy import func

admin = Blueprint('admin', __name__)

@admin.route('/media/<path:filename>')
def get_image(filename):
    return send_from_directory('../media', filename)

@admin.route('/add-shop-items', methods=['GET', 'POST'])
@login_required
def add_shop_items():
    if current_user.id == 1:
        form = ShopItemsForm()

        if form.validate_on_submit():
            product_name = form.product_name.data
            current_price = form.current_price.data
            product_category = form.product_category.data
            in_stock = form.in_stock.data
            flash_sale = form.flash_sale.data

            file = form.product_picture.data

            file_name = secure_filename(file.filename)

            file_path = f'./media/{file_name}'

            file.save(file_path)

            new_shop_item = Product()
            new_shop_item.product_name = product_name
            new_shop_item.current_price = current_price
            new_shop_item.product_category = product_category
            new_shop_item.in_stock = in_stock
            new_shop_item.flash_sale = flash_sale

            new_shop_item.product_picture = file_path

            try:
                db.session.add(new_shop_item)
                db.session.commit()
                flash(f'{product_name} added Successfully')
                print('Product Added')
                return render_template('add_shop_items.html', form=form)
            except Exception as e:
                print(e)
                flash('Product Not Added!!')

        return render_template('add_shop_items.html', form=form)

    return render_template('404.html')


@admin.route('/shop-items', methods=['GET', 'POST'])
@login_required
def shop_items():
    if current_user.id == 1:
        items = Product.query.order_by(Product.date_added).all()
        return render_template('shop_items.html', items=items)
    return render_template('404.html')


@admin.route('/update-item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def update_item(item_id):
    if current_user.id == 1:
        form = ShopItemsForm()

        item_to_update = Product.query.get(item_id)

        form.product_name.render_kw = {'placeholder': item_to_update.product_name}
        form.product_category.render_kw = {'placeholder': 
                                           item_to_update.product_category}
        form.current_price.render_kw = {'placeholder': item_to_update.current_price}
        form.in_stock.render_kw = {'placeholder': item_to_update.in_stock}
        form.flash_sale.render_kw = {'placeholder': item_to_update.flash_sale}

        if form.validate_on_submit():
            product_name = form.product_name.data
            current_price = form.current_price.data
            product_category = form.product_category.data
            in_stock = form.in_stock.data
            flash_sale = form.flash_sale.data

            file = form.product_picture.data

            file_name = secure_filename(file.filename)
            file_path = f'./media/{file_name}'

            file.save(file_path)

            try:
                Product.query.filter_by(id=item_id).update(dict(product_name=product_name,
                                                                current_price=current_price,
                                                                product_category=product_category,
                                                                in_stock=in_stock,
                                                                flash_sale=flash_sale,
                                                                product_picture=file_path))

                db.session.commit()
                flash(f'{product_name} updated Successfully')
                print('Product Upadted')
                return redirect('/shop-items')
            except Exception as e:
                print('Product not Upated', e)
                flash('Item Not Updated!!!')

        return render_template('update_item.html', form=form)
    return render_template('404.html')


@admin.route('/delete-item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def delete_item(item_id):
    if current_user.id == 1:
        try:
            item_to_delete = Product.query.get(item_id)
            db.session.delete(item_to_delete)
            db.session.commit()
            flash('One Item deleted')
            return redirect('/shop-items')
        except Exception as e:
            print('Item not deleted', e)
            flash('Item not deleted!!')
        return redirect('/shop-items')

    return render_template('404.html')


@admin.route('/view-orders')
@login_required
def order_view():
    if current_user.id == 1:
        orders = Order.query.all()
        return render_template('view_orders.html', orders=orders)
    return render_template('404.html')


@admin.route('/update-order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def update_order(order_id):
    if current_user.id == 1:
        form = OrderForm()

        order = Order.query.get(order_id)

        if form.validate_on_submit():
            status = form.order_status.data
            order.status = status

            try:
                db.session.commit()
                flash(f'Order {order_id} Updated successfully')
                return redirect('/view-orders')
            except Exception as e:
                print(e)
                flash(f'Order {order_id} not updated')
                return redirect('/view-orders')

        return render_template('order_update.html', form=form)

    return render_template('404.html')


@admin.route('/customers')
@login_required
def display_customers():
    if current_user.id == 1:
        customers = Customer.query.all()
        return render_template('customers.html', customers=customers)
    return render_template('404.html')


@admin.route('/admin-page')
@login_required
def admin_page():
    if current_user.id == 1:
        return render_template('admin.html')
    return render_template('404.html')


@admin.route('/product-report')
@login_required
def display_product_report():
    if current_user.id == 1:
        report = (
            db.session.query(
                Product.product_name,
                Product.current_price,
                db.func.count(Order.id).label('total_orders'),
                db.func.sum(Order.quantity).label('total_quantity_sold'),
                db.func.sum(Order.quantity * Order.price).label('total_revenue')
            )
            .join(Order, Order.product_link == Product.id)
            .group_by(Product.product_name, Product.current_price)
            .order_by(db.desc('total_revenue'))
            .all()
        )

        return render_template('product_report.html', report=report)

    return render_template('404.html')


@admin.route('/category-report')
@login_required
def display_category_report():
    if current_user.id == 1:

        report = (db.session.query(
            Product.product_category.label('product_category'),
            db.func.count(Order.id).label('total_orders'),
            db.func.sum(Order.quantity).label('total_quantity_sold'),
            db.func.sum(Order.quantity * Order.price).label('total_revenue')
        ).join(Order, Product.id == Order.product_link)
        .group_by(Product.product_category)
        .order_by(db.desc(db.func.sum(Order.quantity * Order.price)))
        .all())

        return render_template('category_report.html', report=report)

    return render_template('404.html')


@admin.route('/monthly-report')
@login_required
def display_monthly_report():
    if current_user.id == 1:

        report = db.session.query(
            func.date_format(Product.date_added, '%Y-%m').label('period'),
            func.count(Order.id).label('total_orders'),
            func.sum(Order.quantity).label('total_quantity_sold'),
            func.sum(Order.quantity * Order.price).label('total_revenue')
        ).join(
            Product, Order.product_link == Product.id
        ).group_by(
            func.date_format(Product.date_added, '%Y-%m')
        ).order_by(
            func.date_format(Product.date_added, '%Y-%m').desc()
        ).all()

        # Pass the report data to the template
        return render_template('monthly_report.html', report=report)
    
    return render_template('404.html')


@admin.route('/repeat-customers-report')
@login_required
def display_repeat_customers_report():
    if current_user.id == 1:
        report = db.session.query(
            Customer.id.label('customer_id'),
            Customer.full_name.label('customer_name'),
            Customer.address.label('customer_address'),
            Customer.email.label('customer_email'), 
            func.count(Order.id).label('total_orders'),
            func.sum(Order.quantity * Order.price).label('total_spent')
        ).join(Order, Customer.id == Order.customer_link) \
         .group_by(Customer.id, Customer.full_name,
                   Customer.address, Customer.email) \
         .having(func.count(Order.id) > 1) \
         .order_by(func.sum(Order.quantity * Order.price).desc()) \
         .all()

        return render_template('repeat_customers_report.html', report=report)
    
    return render_template('404.html')


@admin.route('/product-comparison-report')
@login_required
def display_product_comparison_report():
    if current_user.id == 1:
        report = db.session.query(
            Product.id.label('product_id'),
            Product.product_name.label('product_name'),
            Product.current_price.label('current_price'),
            func.coalesce(func.sum(Order.quantity), 0).label('total_quantity_sold')
        ).outerjoin(Order, Product.id == Order.product_link) \
         .group_by(Product.id, Product.product_name, Product.current_price) \
         .order_by(func.sum(Order.quantity).desc()) \
         .all()

        return render_template('product_comparison_report.html', report=report)
    
    return render_template('404.html')