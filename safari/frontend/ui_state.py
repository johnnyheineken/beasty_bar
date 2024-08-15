import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List
from safari.frontend.frontend import TableCard
from safari.utils.helpers import create_logger

logger = create_logger(__name__)

AI_DELAY = 0.5  # Half a second delay for AI players

class UIStateEnum(Enum):
    MENU = auto()
    SUBMENU = auto()
    GAME = auto()
    END = auto()
    CHAMELEON = auto()
    PARROT = auto()

@dataclass
class UIState:
    current_state: UIStateEnum = UIStateEnum.MENU
    animation_in_progress: bool = False
    last_ai_action_time: float = field(default_factory=time.time)
    chameleon: Optional[TableCard] = None
    table_cards: List[TableCard] = field(default_factory=list)
    hand_cards: List[TableCard] = field(default_factory=list)
    animating_cards: List[TableCard] = field(default_factory=list)
    frame_count: int = 0

    def __post_init__(self):
        logger.info(f"UIState initialized with state: {self.current_state}")

    def change_state(self, new_state: UIStateEnum):
        logger.info(f"Changing state from {self.current_state} to {new_state}")
        self.current_state = new_state

    def start_animation(self):
        logger.debug("Starting animation")
        self.animation_in_progress = True

    def stop_animation(self):
        logger.debug("Stopping animation")
        self.animation_in_progress = False

    def update_ai_action_time(self):
        logger.debug("Updating AI action time")
        self.last_ai_action_time = time.time()

    def is_ai_delay_passed(self) -> bool:
        time_passed = time.time() - self.last_ai_action_time
        logger.debug(f"Checking AI delay: {time_passed:.2f} seconds passed")
        return time_passed >= AI_DELAY

    def set_chameleon(self, card: TableCard):
        logger.info(f"Setting chameleon card: {card}")
        self.chameleon = card

    def clear_chameleon(self):
        logger.info("Clearing chameleon card")
        self.chameleon = None

    def add_animating_card(self, card: TableCard):
        logger.debug(f"Adding animating card: {card}")
        self.animating_cards.append(card)

    def remove_animating_card(self, card: TableCard):
        logger.debug(f"Removing animating card: {card}")
        self.animating_cards.remove(card)

    def update_table_cards(self, new_cards: List[TableCard]):
        logger.info(f"Updating table cards. New count: {len(new_cards)}")
        self.table_cards = new_cards

    def update_hand_cards(self, new_cards: List[TableCard]):
        logger.info(f"Updating hand cards. New count: {len(new_cards)}")
        self.hand_cards = new_cards

    def increment_frame(self):
        self.frame_count += 1
        if self.frame_count % 300 == 0:
            logger.debug(f"Frame {self.frame_count}: Game State - {self.current_state}")