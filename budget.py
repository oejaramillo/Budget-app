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
    percentage = []
    
    numbers = [100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 0]
    graph = []
    lineas = ''
    

    cuentas = []


    



    # Calculamos los porcentajes ####################
    for x in categories:
        withdraws = []
        cuentas.append(x.name)
        for dic in x.ledger:
            clave_amount = list(dic.keys())[0]
            amount_values = dic[clave_amount]

            if amount_values < 0:
                withdraws.append(amount_values)

        spent.append(sum(withdraws))
    
    for x in spent:
        calc = int(((x/sum(spent)*100) // 10)*10)
        percentage.append(calc)

    ##Definimos la salida del gráfico###############
    for x in range(0, len(percentage)):
        spaces = ' '* (11 - int((percentage[x])/10)) + 'o'*int((percentage[x])/10)
        graph.append(spaces)
        
    for x in range(0, 11):
        if len(graph) == 1:
            lineas += '{}| {}\n'.format(str(numbers[x]).rjust(3), graph[0][x])
            guiones = '    '+'-'*4
        elif len(graph) == 2:
            lineas += '{}| {}  {}\n'.format(str(numbers[x]).rjust(3), graph[0][x], graph[1][x])
            guiones = '    '+'-'*7
        elif len(graph) == 3:
            lineas += '{}| {}  {}  {}\n'.format(str(numbers[x]).rjust(3), graph[0][x], graph[1][x], graph[2][x])
            guiones = '    '+'-'*10
        elif len(graph) == 4:
            lineas += '{}| {}  {}  {}  {}\n'.format(str(numbers[x]).rjust(3), graph[0][x], graph[1][x], graph[2][x], graph[3][x])
            guiones = '    '+'-'*13
        elif len(graph) == 5:          
            lineas += '{}| {}  {}  {}  {}  {}\n'.format(str(numbers[x]).rjust(3), graph[0][x], graph[1][x], graph[2][x], graph[3][x], graph[4][x])
            guiones = '    '+'-'*16

    ##Ahora hay que definir los nombres de las cuentas



    return print(title, lineas, guiones.rjust(10),  sep='')
    #return print(cuentas)

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

print(food)
list_c = [food, clothes, business]

create_spend_chart(list_c)


