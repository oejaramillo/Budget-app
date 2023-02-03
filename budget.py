class Category:
    ledger = []
    name = ''
 
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
        self.amount = amount*(-1)
        self.description = description
        
        if self.check_funds(amount) == True:
            self.ledger.append({'amount': self.amount, 'description': self.description})        
            return True
        else:
            self.ledger = self.ledger
            return False

    def transfer(self, amount, category):
        self.amount = amount

        self.withdraw(self.amount, f'Transfer to {category}')
        category.deposit(amount, f'Transfer from {self}')

        if self.ledger == self.ledger:
            return False
        else:
            return True



    



food = Category()
clothing = Category()
food.deposit(200)
clothing.deposit(500)

print(food.get_balance())
