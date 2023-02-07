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

        self.withdraw(self.amount, f'Transfer to {other_category}')
        other_category.deposit(amount, f'Transfer from {self}')

        if self.ledger == self.ledger:
            return False
        else:
            return True

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
            amount = '{}'.format(item['amount']).rjust(6)
            ledger_str += '{} {}\n'.format(description, amount)

        total = '{}'.format(self.get_balance())
        return '{}\n{}Total: {}'.format(cat_title, ledger_str, total)


### Cambiar formato de los números



food = Category('food')
clothes = Category('clothes')

food.deposit(400, 'sueldo')
food.deposit(500, 'regalo')
food.deposit(1000, 'prestamo')
food.withdraw(50, 'pan')
food.withdraw(100, 'ayuda a los ninos de la calle que necesitan ayuda')
food.transfer(90, clothes)

print(food)