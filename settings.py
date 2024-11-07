from fasthtml.common import *
from domain import State
from main import lobby, users
from utils import get_user, update_users
from components import *


@dataclass
class LobbyConfig:
    state_times: dict[State, int]


rt = APIRouter()


def Settings(curr_user: User):
    if not curr_user.is_host: return Div(id='settings')
    return Div(Form(Input(type='number', name='time', value=lobby.game.timer.time), hx_post='/seting'), id='settings')

@rt('/seting')
def post(cfg: LobbyConfig):
    pass


@rt('/pause')
def post(): lobby.game.timer.pause()


@rt('/unpause')
def post(): lobby.game.timer.unpause()


@rt('/update-points')
async def post(sess, user_id: str, points: int = 0):
    u = get_user(sess)
    if not (u and u.is_host): return
    u = users.get(user_id)
    u.add_points(points)
    await update_users(Users)
