class Category:
    ledger = []
    
    def deposit(self, amount, description=''):
        self.amount = amount
        self.description = description
        self.ledger.append({'amount': self.amount, 'description': self.description})
           
        print(self.ledger) 

    def withdraw(self, amount, description=''):
        self.amount = amount*(-1)
        self.description = description
        self.ledger.append({'amount': self.amount, 'description': self.description})        
        
        print(self.ledger)

    def get_balance(self):
        total = 0
        for dic in self.ledger:
            clave_amount = list(dic.keys())[0]
            amount_values = dic[clave_amount]
            total += amount_values

        print(total)


food = Category()
food.deposit(215)
food.deposit(480, 'varios')
food.withdraw(10)
food.deposit(98)
food.deposit(78)
food.deposit(218)
food.withdraw(89)
food.withdraw(100)
food.get_balance()