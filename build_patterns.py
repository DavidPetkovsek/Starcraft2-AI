

class Space:
    def __init__(self, space):
        assert space > 0, "only positive space"
        self.space = space






class LinePattern:

    def __init__(self, cap_design, path_design, iterations):
        self.cap_design = cap_design
        self.path_design = path_design
        self.iterations = iterations

    def __getitem__(self, key):
        assert isinstance(key, int), "the key must be an integer"
        assert key >= 0, "the key must be non negative"

        if key < len(self.cap_design):
            return self.cap_design[key][0]
        elif key < len(self.cap_design) + len(self.path_design)*self.iterations:
            return self.path_design[(key-len(self.cap_design)) % len(self.path_design)][0]
        elif key < len(self.cap_design) * 2 + len(self.path_design)*self.iterations:
            return self.path_design[key-len(self.cap_design)-len(self.path_design)*self.iterations][0]
        else:
            return None

    def __len__(self):
        return len(self.cap_design) * 2 + len(self.path_design)*self.iterations
