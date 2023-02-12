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
    title = 'Percentage spent by category\n'
    spent = []
    numbers = ['100', ' 90', ' 80', ' 70', ' 60', ' 50', ' 40', ' 30', ' 20', ' 10', '  0']
    percentage = []
    
    lineas = []
    graph = ''

    cuentas = []

    # Calculamos el porcentaje en el formato pedido
    for x in categories:
        withdraws = []
        for dic in x.ledger:
            clave_amount = list(dic.keys())[0]
            amount_values = dic[clave_amount]

            if amount_values < 0:
                withdraws.append(amount_values)

        spent.append(sum(withdraws))
    
    for x in spent:
        calc = int(((x/sum(spent)*100) // 10)*10)
        percentage.append(calc)

    # Defnimos las líneas en el formato pedido, las líneas son una lista de strings        
    for y in range(0, 11):
        for x in range(0, len(percentage)):
            
            
            # Hay que definir el segundo corchete que puede variar
            lineas.append('{}| {}\n'.format(numbers[y], x))

    # Se defie el gráfico
    for x in range(0, 11):
        graph += '{}'.format(lineas[x])
    
    return print(title, graph, sep='')

    

food = Category('food')
clothes = Category('clothes')
business = Category('business')

food.deposit(100, 'ganancias de capital')
clothes.deposit(500, 'donando por un senor')
business.deposit(98.25, 'ingesos por trabajo')
food.deposit(78.65, 'encontrado')
clothes.deposit(7821.36, 'encontrad')

food.withdraw(879.25, 'comida')
food.withdraw(45.12, 'regalo')
business.withdraw(9.65, 'perdido')
clothes.withdraw(69.47, 'pantalon comprado')

food.transfer(100, business)
food.transfer(50.12, clothes)
clothes.transfer(146.35, food)
clothes.transfer(36.85, business)

list_c = [food, clothes, business]

create_spend_chart(list_c)


