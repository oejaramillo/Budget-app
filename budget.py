class Category:
    def __init__(self, name):
        self.ledger = []
        self.name = name
        self.amount = 0
        self.description = ''

    def check_funds(self, amount):
        if amount <= self.get_balance():
            return True
        else:
            return False

    def get_balance(self):
        total = 0
        for dic in self.ledger:
            clave_amount = list(dic.keys())[0]
            amount_values = dic[clave_amount]
            total += amount_values

        return total

    def deposit(self, amount, description=''):
        self.amount = float(amount)
        self.description = description
        self.ledger.append({'amount': self.amount, 'description': self.description})

    def withdraw(self, amount, description=''):
        self.amount = float(amount) * -1
        self.description = description

        if self.check_funds(amount) == True:
            self.ledger.append({'amount': self.amount, 'description': self.description})        
            return True
        else:
            return False

    def transfer(self, amount, other_category):
        self.amount = float(amount)

        if self.amount <= self.get_balance():
            self.withdraw(self.amount, f'Transfer to {other_category.name}')
            other_category.deposit(amount, f'Transfer from {self.name}')

            return True

        else:
            return False
            
    def __str__(self):
        title_pos = 15-len(self.name)//2
        f_asterics = '*' * int(title_pos)
        b_asterics = '*' * (int(title_pos)-1)

        if len(self.name) % 2 == 0:
            cat_title = f'{f_asterics}{self.name}{f_asterics}'
        else:
            cat_title = f'{f_asterics}{self.name}{b_asterics}'

        ledger_str = ''
        for item in self.ledger:
            description = item['description'][:23].ljust(23)
            amount = '{:.2f}'.format(item['amount'])[:7].rjust(7)
            ledger_str += '{}{}\n'.format(description, amount)

        total = '{:.2f}'.format(self.get_balance())
        return '{}\n{}Total: {}'.format(cat_title, ledger_str, total)


def create_spend_chart(categories):
    spent = [sum([item['amount'] for item in category.ledger if item['amount'] < 0]) for category in categories]
    total_spent = sum(spent)
    percentages = [int(spent_category / total_spent * 10) * 10 for spent_category in spent]
     
    # Create chart lines
    chart_lines = []
    for i in range(100, -10, -10):
        chart_line = "{:>3}| ".format(i)
        for percentage in percentages:
            if percentage >= i:
                chart_line += "o  "
            else:
                chart_line += "   "
        chart_lines.append(chart_line)

    # Create category names and legend
    category_names = [category.name for category in categories]
    longest_name_length = max([len(name) for name in category_names])
    category_names = [name.ljust(longest_name_length) for name in category_names]

    category_legend_lines = []
    for i in range(longest_name_length):
        category_legend_line = "     "
        for name in category_names:
            if i < len(name):
                category_legend_line += name[i] + "  "
            else:
                category_legend_line += "   "
        category_legend_lines.append(category_legend_line)

    # Combine chart and legend
    chart = "\n".join(chart_lines)
    category_legend = "\n".join(category_legend_lines)
    chart_with_legend = "{}\n{}\n{}\n{}\n".format(
        "Percentage spent by category",
        chart, "    " + "-" * (len(category_names) * 3 + 1),
        category_legend
    )

    return chart_with_legend 




food = Category('food')
business = Category('business')
entertainment = Category('entretainment')

food.deposit(900, "deposit")
entertainment.deposit(900, "deposit")
business.deposit(900, "deposit")
food.withdraw(105.55)
entertainment.withdraw(33.40)
business.withdraw(10.99)

list_c = [business, food, entertainment]
replit = 'Percentage spent by category\n100|          \n 90|          \n 80|          \n 70|    o     \n 60|    o     \n 50|    o     \n 40|    o     \n 30|    o     \n 20|    o  o  \n 10|    o  o  \n  0| o  o  o  \n    ----------\n     B  F  E  \n     u  o  n  \n     s  o  t  \n     i  d  e  \n     n     r  \n     e     t  \n     s     a  \n     s     i  \n           n  \n           m  \n           e  \n           n  \n           t  '

print(create_spend_chart(list_c))
print(replit)
