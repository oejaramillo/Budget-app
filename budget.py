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
        self.amount = amount
        self.description = description
        self.ledger.append({'amount': self.amount, 'description': self.description})

    def withdraw(self, amount, description=''):
        self.amount = amount * -1
        self.description = description

        if self.check_funds(amount) == True:
            self.ledger.append({'amount': self.amount, 'description': self.description})        
            return True
        else:
            return False

    def transfer(self, other_category, amount):
        self.amount = amount

        self.withdraw(self.amount, f'Transfer to {other_category}')
        other_category.deposit(amount, f'Transfer from {self}')

        if self.ledger == self.ledger:
            return False
        else:
            return True


clothes = Category('clothes')
clothes.deposit(400)
clothes.deposit(100)
clothes.withdraw(50)
print(clothes.check_funds(100))
print(clothes.get_balance())
print(clothes.withdraw(500))

food = Category('food')
food.deposit(400)
food.deposit(100)
food.withdraw(50)
print(food.check_funds(100))
print(food.get_balance())
print(food.withdraw(500))

food.transfer(clothes, 200)
print(clothes.get_balance())
print(food.get_balance())