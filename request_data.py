class Request:
    def __init__(self, lang):
        self.lang: str = 'ru'
        self.last_message_id: int = None
        self.last_message_text: str = None
        self.last_message_keyboard: dict = None
        self.chat_id: int = None
        self.command: str = None
        self.city: str = None
        self.min_price: int = None
        self.max_price: int = None
        self.distance: int = None
        self.search_results: int = None
        self.destinashionID: int = None




