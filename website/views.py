from flask import Blueprint, render_template, flash, redirect, request, jsonify
from .models import Product, Cart, Order
from flask_login import login_required, current_user
from . import db
import paypalrestsdk


views = Blueprint('views', __name__)
client_id = "Adjsp4daPZ_vGyGeuKMEQ3vLyGluZliLy21UJwjpR8gWp_atgaAQLEIoSHVurfljLsYXc3lq7S78Oa6q"

clien_sec = "ECEFS5QVPcmeTWlTfQIW4S3_4VxjGkwiQBZgdfGZ7J434hg2251HXYtVX0eHt0oWW3QQSkt8WRb5Rjx9"
paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": client_id,
    "client_secret": clien_sec
})

@views.route('/')
def home():
    items = Product.query.filter_by(flash_sale=True)
    return render_template('home.html', items=items,
                           cart=Cart.query.filter_by(customer_link=current_user.id).all()
                           if current_user.is_authenticated else [])

@views.route('/category')
def home_category():
    category = request.args.get('category')
    
    items = Product.query.filter_by(product_category=category).all()
    return render_template('home.html', items=items,
                           cart=Cart.query.filter_by(customer_link=current_user.id).all()
                           if current_user.is_authenticated else [])


@views.route('/add-to-cart/<int:item_id>')
@login_required
def add_to_cart(item_id):
    item_to_add = Product.query.get(item_id)
    item_exists = Cart.query.filter_by(product_link=item_id,
                                       customer_link=current_user.id).first()
    if item_exists:
        try:
            item_exists.quantity += 1
            valu_up = item_exists.product.product_name
            db.session.commit()
            flash(f'Quantity of {valu_up} has been updated')
            return redirect(request.referrer)
        except Exception as e:
            print('Quantity not updated:', e)
            flash(f'Quantity of {item_exists.product.product_name} not updated')
            return redirect(request.referrer)

    new_cart_item = Cart(quantity=1, product_link=item_to_add.id,
                         customer_link=current_user.id)
    try:
        db.session.add(new_cart_item)
        db.session.commit()
        flash(f'{new_cart_item.product.product_name} added to cart')
    except Exception as e:
        print('Item not added to cart:', e)
        flash(f'{new_cart_item.product.product_name} has not been added to cart')
    return redirect(request.referrer)

@views.route('/cart')
@login_required
def show_cart():
    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)
    return render_template('cart.html', cart=cart, amount=amount, total=amount+200)

@views.route('/pluscart')
@login_required
def plus_cart():
    cart_id = request.args.get('cart_id')
    cart_item = Cart.query.get(cart_id)
    cart_item.quantity += 1
    db.session.commit()

    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)

    data = {
        'quantity': cart_item.quantity,
        'amount': amount,
        'total': amount + 30
    }
    return jsonify(data)

@views.route('/minuscart')
@login_required
def minus_cart():
    cart_id = request.args.get('cart_id')
    cart_item = Cart.query.get(cart_id)
    cart_item.quantity -= 1
    db.session.commit()

    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)

    data = {
        'quantity': cart_item.quantity,
        'amount': amount,
        'total': amount + 30
    }
    return jsonify(data)

@views.route('/removecart')
@login_required
def remove_cart():
    cart_id = request.args.get('cart_id')
    cart_item = Cart.query.get(cart_id)
    db.session.delete(cart_item)
    db.session.commit()

    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)

    data = {
        'quantity': cart_item.quantity,
        'amount': amount,
        'total': amount + 30
    }
    return jsonify(data)

@views.route('/place-order')
@login_required
def place_order():
    customer_cart = Cart.query.filter_by(customer_link=current_user.id).all()
    if customer_cart:
        try:
            item_prices = []
            for item in customer_cart:
                price = item.product.current_price * item.quantity
                item_prices.append(price)
            total = sum(item_prices)

            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "transactions": [{
                    "amount": {
                        "total": str(total + 30),
                        "currency": "USD"
                    },
                    "description": "Purchase of goods"
                }],
                "redirect_urls": {
                    "return_url": "http://localhost:5000/payment/execute",
                    "cancel_url": "http://localhost:5000/"
                }
            })

            if payment.create():
                for item in customer_cart:
                    new_order = Order(
                        quantity=item.quantity,
                        price=item.product.current_price,
                        status="Pending",
                        payment_id=payment.id,
                        product_link=item.product_link,
                        customer_link=item.customer_link
                    )
                    db.session.add(new_order)

                    product = Product.query.get(item.product_link)
                    product.in_stock -= item.quantity
                    db.session.delete(item)

                db.session.commit()
                flash('Order Placed Successfully')

                # Redirect user to PayPal for payment approval
                for link in payment.links:
                    if link.rel == "approval_url":
                        return redirect(link.href)
            else:
                flash('Payment creation failed')
                return redirect('/')
        except Exception as e:
            print(e)
            flash('Order not placed')
            return redirect('/')
    else:
        flash('Your cart is empty')
        return redirect('/')

@views.route('/payment/execute')
@login_required
def execute_payment():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        flash('Payment successful')
    else:
        flash('Payment failed')

    return redirect('/orders')

@views.route('/orders')
@login_required
def order():
    orders = Order.query.filter_by(customer_link=current_user.id).all()
    return render_template('orders.html', orders=orders)

@views.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form.get('search')
        items = Product.query.filter(
            Product.product_name.ilike(f'%{search_query}%')
        ).all()

        cart_items = Cart.query.filter_by(
            customer_link=current_user.id
        ).all() if current_user.is_authenticated else []

        return render_template(
            'search.html',
            items=items,
            cart=cart_items
        )
    
    return render_template('search.html')
