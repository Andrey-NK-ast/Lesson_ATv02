from flask import Flask, render_template, request, redirect, url_for
import math

app = Flask(__name__)

@app.template_filter('money')
def money_format(value):
    try:
        parts = f"{value:,.0f}".split(',')
        return ' '.join(parts)
    except Exception:
        return value

@app.route('/')
def index():
    """Главная страница с формой ввода"""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """Обработка формы и расчет ипотеки"""
    try:
        loan_amount = float(request.form.get('loan_amount', 0))
        interest_rate = float(request.form.get('interest_rate', 0))
        loan_term = int(request.form.get('loan_term', 0))
        term_unit = request.form.get('term_unit', 'months')
        down_payment = float(request.form.get('down_payment', 0))
        
        # Переводим срок в месяцы, если пользователь указал годы
        if term_unit == 'years':
            loan_term = loan_term * 12

        # Досрочное погашение
        use_early = request.form.get('early_repay_check', '') == 'on'
        early_amount = float(request.form.get('early_amount').replace(' ', '') or 0) if use_early else 0
        early_frequency = request.form.get('early_frequency', 'once') if use_early else 'once'
        early_method = request.form.get('early_method', '') if use_early else ''
        def is_early_payment_period(month):
            if not use_early:
                return False
            if early_frequency == 'once':
                return month == 2  # по умолчанию разово во 2-й месяц, можно сделать настройку
            if early_frequency == 'monthly':
                return month >= 2  # каждый месяц начиная со второго
            if early_frequency == '2months':
                return month >= 2 and (month - 2) % 2 == 0
            if early_frequency == 'quarter':
                return month >= 2 and (month - 2) % 3 == 0
            if early_frequency == 'halfyear':
                return month >= 2 and (month - 2) % 6 == 0
            if early_frequency == 'year':
                return month >= 2 and (month - 2) % 12 == 0
            return False
        
        if loan_amount <= 0 or interest_rate < 0 or loan_term <= 0 or down_payment < 0:
            return redirect(url_for('index'))
        if down_payment >= loan_amount:
            return redirect(url_for('index'))
       
        principal = loan_amount - down_payment
        monthly_rate = (interest_rate / 12) / 100
        
        def calc_annuity_payment(P, r, n):
            if r == 0:
                return P / n
            return P * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        
        monthly_payment = calc_annuity_payment(principal, monthly_rate, loan_term)
        payment_schedule = []
        remaining_balance = principal
        month = 1
        # до досрочного погашения
        while month <= loan_term:
            interest_payment = remaining_balance * monthly_rate
            principal_payment = monthly_payment - interest_payment
            remaining_balance -= principal_payment
            if use_early and is_early_payment_period(month):
                remaining_balance -= early_amount
                if remaining_balance < 0:
                    principal_payment += remaining_balance
                    remaining_balance = 0
            payment_schedule.append({
                'month': month,
                'payment': round(monthly_payment, 2),
                'principal': round(principal_payment, 2),
                'interest': round(interest_payment, 2),
                'remaining': round(remaining_balance, 2)
            })
            # если досрочное погашение произошло — меняем алгоритм
            if use_early and is_early_payment_period(month):
                if early_method == 'decrease_payment' and remaining_balance > 0:
                    rest_n = loan_term - month
                    monthly_payment = calc_annuity_payment(remaining_balance, monthly_rate, rest_n)
                elif early_method == 'decrease_term' and remaining_balance > 0:
                    # подбираем минимальное n, чтобы платеж остался тем же
                    rest_n = 1
                    while rest_n <= (loan_term - month):
                        p = calc_annuity_payment(remaining_balance, monthly_rate, rest_n)
                        if p <= monthly_payment:
                            break
                        rest_n += 1
                    term_left = rest_n
                    loan_term = month + term_left
                # else: ничего не делать
            if remaining_balance <= 0:
                break
            month += 1
        total_payment = sum(p['payment'] for p in payment_schedule)
        principal_total = sum(p['principal'] for p in payment_schedule)
        interest_total = sum(p['interest'] for p in payment_schedule)
        return render_template('result.html',
                             loan_amount=loan_amount,
                             down_payment=down_payment,
                             principal=principal,
                             interest_rate=interest_rate,
                             loan_term=len(payment_schedule),
                             monthly_payment=payment_schedule[0]['payment'],
                             total_payment=round(total_payment, 2),
                             payment_schedule=payment_schedule,
                             principal_total=round(principal_total, 2),
                             interest_total=round(interest_total, 2))
    except (ValueError, TypeError):
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

