import datetime
import math
import random
import time

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func, desc, update, asc, select
from sqlalchemy.sql.functions import now, random as sqrandom

from Utilities.database.postgres import env
from Utilities.database.postgres.env import bot_engine, BotBase
from Utilities.database.postgres.models import users, hubcoins, diminishing_returns as dr, cache, creations


def _generate_links(results, at_least):
    filtered_links = [f"[[{index}](<{image.url}>)] {{{image.user.deviant_username}}}"
                      for index, image in enumerate(results[:at_least], start=1)]
    return ", ".join(filtered_links)


def format_cache_result(result):
    nl = '\n'
    clean_snippet = result['src_snippet'].replace("<br />", nl).replace("%", "%%")
    clean_title = result['title'].replace("'", "").replace("%", "%%")
    tags = ','.join([tag['tag_name'] for tag in result['tags']]) if 'tags' in result.keys() else None
    formatted_dt = datetime.datetime.fromtimestamp(int(result['published_time'])).strftime('%Y%m%d')
    return clean_snippet, clean_title, formatted_dt, tags


####

def _session_execute(statement):
    with env.BotSessionLocal() as session:
        return session.execute(statement)


####

def daily_clear():
    # query = "TRUNCATE TABLE diminishing_returns_table"
    BotBase.metadata.drop_all(bot_engine, tables=[dr.DiminishingReturns.__table__])
    BotBase.metadata.create_all(bot_engine, tables=[dr.DiminishingReturns.__table__])


def store_da_name(discord_id, username):
    # f"INSERT INTO deviant_usernames (discord_id, deviant_username) VALUES ({discord_id}, '{username}') " \
    #         f"ON CONFLICT (discord_id) DO UPDATE SET deviant_username=excluded.deviant_username"
    new_hubber = insert(users.Hubbers).values(discord_id=discord_id, username=username)
    new_hubber.on_conflict_do_update(
        constraint="discord_id", set_=dict(deviant_username=new_hubber.excluded.deviant_username)
    )
    _session_execute(new_hubber)


def store_random_da_name(username):
    # query = f"INSERT INTO deviant_usernames (ping_me, deviant_username) VALUES (false, '{username}') "
    store_random_hubber = insert(users.Hubbers).values(ping_me=False, deviant_username=username)
    store_random_hubber.on_conflict_do_update(
        constraint="discord_id", set_=dict(deviant_username=store_random_hubber.excluded.deviant_username)
    )
    _session_execute(store_random_hubber)


def do_not_ping_me(discord_id):
    # query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, false) " \
    #         f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
    store_hubber = insert(users.Hubbers).values(discord_id=discord_id, ping_me=False)
    store_hubber.on_conflict_do_update(
        constraint="discord_id", set_=dict(ping_me=store_hubber.excluded.ping_me)
    )
    _session_execute(store_hubber)


def ping_me(discord_id):
    # query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, true) " \
    #         f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
    store_hubber = insert(users.Hubbers).values(discord_id=discord_id, ping_me=True)
    store_hubber.on_conflict_do_update(
        constraint="discord_id", set_=dict(ping_me=store_hubber.excluded.ping_me)
    )
    _session_execute(store_hubber)


def fetch_username(discord_id):
    # query = f"Select id, deviant_username from deviant_usernames where discord_id = {discord_id}"
    # if result._mapping["deviant_username"] is not None:
    #     return result._mapping["deviant_username"]
    # return int(result._mapping["id"])
    with env.BotSessionLocal() as db:
        selected_user = db.scalars(select(users.Hubbers).where(
            users.Hubbers.discord_id == discord_id and users.Hubbers.ping_me == False
        )).first()
    if selected_user is None:
        return None
    if selected_user.deviant_username is not None:
        return selected_user.deviant_username
    return selected_user.id

def fetch_pop_from_cache(deviant_row_id, display_num):
    # query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id}
    #         order by favs desc
    #         limit {display_num} """
    with env.BotSessionLocal() as db:
        return db.scalars(select(creations.Creations).where(
            creations.Creations.deviant_user_row == deviant_row_id
        ).order_by(
            desc(creations.Creations.favs)
        ).limit(
            display_num
        )).all()


def fetch_entire_user_gallery(deviant_row_id):
    # query = f""" SELECT * from deviations where deviant_user_row = {deviant_row_id}
    #     order by date_created desc """
    with env.BotSessionLocal() as db:
        return db.scalars(select(creations.Creations).where(
            creations.Creations.deviant_user_row == deviant_row_id
        ).order_by(
                desc(creations.Creations.date_created)
        )).all()

def fetch_user_devs_by_tag(deviant_row_id, display_num, tags):
    # query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id} and
    #                 position('{tags}' in tags) > 0
    #                 order by date_created desc
    #                 limit {display_num} """
    with env.BotSessionLocal() as db:
        return db.scalars(select(creations.Creations).filter(
            creations.Creations.deviant_user_row == deviant_row_id
        ).filter(
            creations.Creations.tags.contains(tags)
        ).order_by(
            desc(creations.Creations.date_created)
        ).limit(
            display_num
        )).all()

def fetch_old_from_cache(deviant_row_id, display_num):
    # query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id}
    #         order by date_created asc
    #         limit {display_num} """
    with env.BotSessionLocal() as db:
        return db.scalars(select(creations.Creations).filter(
                creations.Creations.deviant_user_row == deviant_row_id
            ).order_by(
                asc(creations.Creations.date_created)
            ).limit(
                display_num
            )).all()

def get_tormund():
    with env.BotSessionLocal() as db:
        results = db.scalars(select(creations.Creations).filter_by(
            deviant_user_row=2
        ).filter(
            creations.Creations.tags.contains("tormund")
        ).order_by(
            sqrandom()
        )).all()
        return results

def fetch_discord_id(username):
    # query = f"Select discord_id from deviant_usernames where lower(deviant_username) = '{username.lower()}' " \
    #         f"and ping_me = true" if isinstance(username, str) else \
    #     f"Select discord_id from deviant_usernames where id = {username} " \
    #         f"and ping_me = true"
    with env.BotSessionLocal() as db:
        selected_user = db.scalars(select(users.Hubbers).where(
            func.lower(users.Hubbers.deviant_username) == username.lower()
        )).first()
    if selected_user is None:
        return None
    return selected_user.discord_id


def add_coins(discord_id, username):
    # get discord_id for username, if exists, make sure no cheaters
    if username:
        # query = f""" SELECT discord_id from deviant_usernames where lower(deviant_username) = '{username.lower()}'
        #         """ if isinstance(username, str) else \
        #     f""" SELECT discord_id from deviant_usernames where id = {username} """

        with env.BotSessionLocal() as db:
            possible_id = db.scalars(select(users.Hubbers).where(
                    func.lower(users.Hubbers.deviant_username) == username.lower()
                )).first() if isinstance(username, str) else \
                db.scalars(select(users.Hubbers).where(
                    users.Hubbers.id == username
                )).first()
        if possible_id:
            user_discord_id = possible_id.discord_id
            if user_discord_id == discord_id:
                # dirty cheater
                pass
            else:
                # do both
                update_coins(discord_id, 2)
                if user_discord_id:
                    # could be none
                    update_coins(user_discord_id, 1)
        else:
            # username wasn't in store
            update_coins(discord_id, 2)
    else:
        # username wasn't in store
        update_coins(discord_id, 2)


def spend_coins(discord_id, amount):
    update_coins(discord_id, -amount)


def get_hubcoins(discord_id, column):
    # get current coins and return the count
    # query = f""" SELECT {column} from hubcoins where discord_id = {discord_id} """
    with env.BotSessionLocal() as db:
        coins = db.scalars(select(hubcoins.Hubcoins).where(
            hubcoins.Hubcoins.discord_id == discord_id
        )).first()
        if coins is not None:
            return getattr(coins, column, 0)
        else:
            # query = f""" INSERT into hubcoins (discord_id) values ({discord_id}) """
            coin_query = insert(hubcoins.Hubcoins).values(discord_id=discord_id)
            _session_execute(coin_query)
            return 0


def update_coins(discord_id, amount):
    coins = get_hubcoins(discord_id, "hubcoins")
    # add_query = f""" UPDATE hubcoins set hubcoins = {coins + amount} where discord_id = {discord_id} """
    add_query = update(hubcoins.Hubcoins).values(hubcoins=coins + amount).where(
        hubcoins.Hubcoins.discord_id == discord_id)
    _session_execute(add_query)
    if amount < 0:
        # spent_query = f""" UPDATE hubcoins set spent_coins = spent_coins - {amount} where discord_id = {
        # discord_id}  """
        spent_query = update(users.Hubbers).where(users.Hubbers.discord_id == discord_id).values(
            hubcoins=hubcoins.Hubcoins.coins + amount
        )
        _session_execute(spent_query)


def get_role_added(discord_id, column):
    # get current coins and return the count
    # query = f""" SELECT {column} from role_assignment_date where discord_id = {discord_id} """
    with env.BotSessionLocal() as db:
        row = db.scalars(select(cache.RoleColorAssignment).filter_by(
            cache.RoleColorAssignment.discord_id == discord_id
        )).first()
        return row.get(column, 0)


def add_role_timer(discord_id, role_color):
    date = get_role_added(discord_id, "last_added_timestamp")
    # change to upsert
    if not date:
        # query = f""" INSERT into role_assignment_date (discord_id, role_color) values ({discord_id},
        #         '{role_color}') """
        _session_execute(insert(cache.RoleColorAssignment).values(
            discord_id=discord_id, role_color=role_color
        )).first()
    else:
        # add_query = f""" UPDATE role_assignment_date set last_added_timestamp = NOW(),
        #             role_color = '{role_color}' where discord_id = {discord_id}"""
        _session_execute(update(cache.RoleColorAssignment).where(
            cache.RoleColorAssignment.discord_id == discord_id
        ).values(
            discord_id=discord_id, role_color=role_color
        )).first()


def delete_role(discord_ids):
    # query = f""" DELETE from role_assignment_date where discord_id in ({", ".join(discord_ids)}) """
    with env.BotSessionLocal() as db:
        rows = db.scalars(select(cache.RoleColorAssignment).filter(
            cache.RoleColorAssignment.discord_id.in_(discord_ids)
        )).all()
        db.session.delete(rows)


def get_all_expiring_roles():
    # query = f""" SELECT * from role_assignment_date"""
    with env.BotSessionLocal() as db:
        rows = db.scalars(select(cache.RoleColorAssignment)).all()
    current_time = datetime.datetime.now()
    compare_against = time.mktime(current_time.timetuple())
    roles_expiring = []
    for row in rows:
        timestamp = row.last_added_timestamp
        comparison = time.mktime(timestamp.timetuple())
        if abs(comparison - compare_against) > 604800:
            roles_expiring.append([row.discord_id, row.role_color])
    return roles_expiring


def refresh_message_counts():
    daily_clear()


def diminish_coins_added(deviant_id):
    # query = f"""INSERT INTO diminishing_returns_table (deviant_id)
    #             VALUES({deviant_id})
    #             ON CONFLICT (deviant_id)
    #             DO UPDATE set message_count = diminishing_returns_table.message_count + 1
    #             RETURNING message_count """
    diminish_query = insert(dr.DiminishingReturns).values(deviant_id=deviant_id)
    diminish_query.on_conflict_do_update(
        constraint="deviant_id", set_=dict(message_count=diminish_query.excluded.message_count + 1)
    )
    diminish_by = _session_execute(diminish_query).first()
    max_percent_reduction = 0.95
    k = 0.043
    return round(max_percent_reduction * (1 - math.exp(-k * diminish_by[0])), 6)


def fetch_da_usernames(num):
    # query = f"Select deviant_username from deviant_usernames where deviant_username is not null"
    with env.BotSessionLocal() as db:
        da_usernames = db.scalars(select(users.Hubbers.deviant_username).where(
            users.Hubbers.deviant_username is not None)).all()
    query_results = ["".join(name_tuple) for name_tuple in da_usernames]
    random.shuffle(query_results)
    return query_results[:num]


def get_random_images(num):
    # query = f"""SELECT title, is_mature, url, src_image, src_snippet , deviant_username as author
    #             FROM deviant_usernames INNER JOIN deviations
    #             ON deviations.deviant_user_row = deviant_usernames.id order by random() limit {num} """
    with env.BotSessionLocal() as db:
        results = db.scalars(select(creations.Creations).order_by(
            sqrandom()
        ).join(
            users.Hubbers, creations.Creations.deviant_user_row == users.Hubbers.id
        )).all()
        return results, _generate_links(results, num)


def user_last_cache_update(username):
    user_id_row = fetch_user_row_id(username)
    if not user_id_row:
        return None
    with env.BotSessionLocal() as db:
        # query = f"""SELECT last_updated from cache_updated_date where deviant_row_id = {user_id_row}"""
        last_updated = db.scalars(select(cache.Cache).filter_by(deviant_row_id=user_id_row)).first()
    return last_updated


def fetch_user_row_id(username):
    # query = f"Select id from deviant_usernames where lower(deviant_username) = '{username.lower()}' " if \
    #     isinstance(username, str) else \
    #     f"Select id from deviant_usernames where id = {username} "
    with env.BotSessionLocal() as db:
        result = db.scalars(select(users.Hubbers.id).where(
            func.lower(users.Hubbers.deviant_username) == username.lower()
        )).first() \
            if isinstance(username, str) else \
            db.scalars(select(users.Hubbers.id).filter_by(id=username)).first()
    return result


def initial_add_to_cache(results, row_id):
    for result in results:
        clean_snippet, clean_title, formatted_dt, tags = format_cache_result(result)
        # query = f"INSERT INTO deviations (deviant_user_row, url, src_image, src_snippet, title, favs, tags, " \
        #         f"date_created, is_mature) VALUES {values_list} ON CONFLICT (url) DO UPDATE set favs=excluded.favs, " \
        #         f"title=excluded.title, tags=excluded.tags, is_mature=excluded.is_mature, src_image=excluded.src_image, " \
        #         f"src_snippet=excluded.src_snippet"

        deviation_insert = insert(creations.Creations).values(
            deviant_user_row=row_id, url=result['url'], src_image=result['src_image'], src_snippet=clean_snippet,
            title=clean_title, favs=result['stats']['favourites'], tags=tags, date_created=formatted_dt,
            is_mature=result['is_mature']
        )
        deviation_insert.on_conflict_do_update(
            constraint="url", set_=dict(
                favs=deviation_insert.excluded.favs, title=deviation_insert.excluded.title,
                tags=deviation_insert.excluded.tags, is_mature=deviation_insert.excluded.is_mature,
                src_image=deviation_insert.excluded.src_image, src_snippet=deviation_insert.excluded.src_snippet
            )
        )
        _session_execute(deviation_insert)
        update_da_cache(row_id)


def update_da_cache(row_id):
    # query = (f"INSERT INTO cache_updated_date (deviant_row_id) VALUES ({row_id}) ON CONFLICT "
    #          f"(deviant_row_id) DO UPDATE SET last_updated = now()")
    cache_update = insert(cache.Cache).values(
        deviant_row_id=row_id
    )
    cache_update.on_conflict_do_update(constraint="deviant_row_id", set_=dict(last_updated=now()))
    _session_execute(cache_update)
