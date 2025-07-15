class LexEnv:
    def __init__(self, declaring_method, parent_lexenv=None):
        self.parent_lexenv = parent_lexenv
        if self.parent_lexenv:
            self.lexenv_level = self.parent_lexenv.lexenv_level + 1
        else:
            self.lexenv_level = 0
        self.declaring_method = declaring_method
        self.lexvars = []

    def add_lexvar(self, lexvar):
        self.lexvars.append(lexvar)

    def get_lexvar(self, i):
        if i > len(self.lexvars):
            raise IndexError(f'{self.__class__.__name__}: Lexvar index {i} out of bounds')
        return self.lexvars[i]
