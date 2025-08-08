import datetime
import math
import time

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func, desc, update, asc, select
from sqlalchemy.sql.functions import now, random as sqrandom

from Classes.database.postgres import env
from Classes.database.postgres.env import bot_engine, BotBase
from Classes.database.postgres.models import users, hubcoins, diminishing_returns as dr, cache, creations


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
    with env.BotSessionLocal() as db:
        new_hubber = users.Hubbers(discord_id=discord_id, deviant_username=username)
        new_hubber_exists = db.scalars(select(users.Hubbers).filter_by(discord_id=discord_id)).first()
        if new_hubber_exists:
            new_hubber_exists.deviant_username = username
            return db.commit()
        db.add(new_hubber)
        return db.commit()


def store_random_da_name(username):
    # query = f"INSERT INTO deviant_usernames (ping_me, deviant_username) VALUES (false, '{username}') "
    with env.BotSessionLocal() as db:
        new_hubber_exists = db.scalars(select(users.Hubbers).filter_by(deviant_username=username)).first()
        if not new_hubber_exists:
            new_hubber = users.Hubbers(deviant_username=username)
            db.add(new_hubber)
            return db.commit()


def do_not_ping_me(discord_id):
    # query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, false) " \
    #         f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
    with env.BotSessionLocal() as db:
        hubber = db.scalars(select(users.Hubbers).filter_by(discord_id=discord_id, ping_me=True)).first()
        if hubber:
            hubber.ping_me = False
            return db.commit()


def ping_me(discord_id):
    # query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, true) " \
    #         f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
    with env.BotSessionLocal() as db:
        hubber = db.scalars(select(users.Hubbers).filter_by(discord_id=discord_id, ping_me=False)).first()
        if hubber:
            hubber.ping_me = True
            return db.commit()


def fetch_username(discord_id):
    # query = f"Select id, deviant_username from deviant_usernames where discord_id = {discord_id}"
    # if result._mapping["deviant_username"] is not None:
    #     return result._mapping["deviant_username"]
    # return int(result._mapping["id"])
    with env.BotSessionLocal() as db:
        selected_user = db.scalars(select(users.Hubbers).filter_by(discord_id=discord_id)).first()
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


def fetch_server_popular():
    # query = f""" SELECT * from deviations where deviant_user_row = {deviant_row_id}
    #     order by date_created desc """
    with env.BotSessionLocal() as db:
        return db.scalars(select(creations.Creations).order_by(
            desc(creations.Creations.favs)
        ).order_by(
            desc(creations.Creations.comments)
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


def fetch_discord_id(username: str):
    # query = f"Select discord_id from deviant_usernames where lower(deviant_username) = '{username.lower()}' " \
    #         f"and ping_me = true" if isinstance(username, str) else \
    #     f"Select discord_id from deviant_usernames where id = {username} " \
    #         f"and ping_me = true"
    with env.BotSessionLocal() as db:
        selected_user = db.scalars(
            select(users.Hubbers)
            .filter(
                func.lower(users.Hubbers.deviant_username) == username.lower())
            .filter_by(
                ping_me=True
            )
        ).first()
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
        coins = db.scalars(select(hubcoins.Hubcoins).filter_by(discord_id=discord_id)).first()
        if coins is not None:
            return getattr(coins, column, 0)
        else:
            # query = f""" INSERT into hubcoins (discord_id) values ({discord_id}) """
            coin_query = insert(hubcoins.Hubcoins).values(discord_id=discord_id)
            _session_execute(coin_query)
            return 0


def update_coins(discord_id: int, amount: int):
    coins = get_hubcoins(discord_id, "hubcoins")
    # add_query = f""" UPDATE hubcoins set hubcoins = {coins + amount} where discord_id = {discord_id} """
    add_query = update(hubcoins.Hubcoins).values(
        hubcoins=coins + amount
    ).where(
        hubcoins.Hubcoins.discord_id == discord_id
    )
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
        row = db.scalars(select(cache.RoleColorAssignment).filter(
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


def delete_role(discord_ids: list[int]):
    # query = f""" DELETE from role_assignment_date where discord_id in ({", ".join(discord_ids)}) """
    with env.BotSessionLocal() as db:
        rows = db.scalars(select(cache.RoleColorAssignment).filter(
            cache.RoleColorAssignment.discord_id.in_(discord_ids)
        )).all()
        db.delete(rows)
        db.commit()


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

    with env.BotSessionLocal() as db:
        diminished = db.scalars(select(dr.DiminishingReturns).filter_by(deviant_id=deviant_id)).first()
        if diminished:
            diminished.message_count = diminished.message_count + 1
            db.commit()
        else:
            diminished = dr.DiminishingReturns(deviant_id=deviant_id, message_count=1)
            db.add(diminished)
            db.commit()
        diminished_by = diminished.message_count
    max_percent_reduction = 0.95
    k = 0.043
    return round(max_percent_reduction * (1 - math.exp(-k * diminished_by)), 6)


def fetch_da_usernames(num):
    # query = f"Select deviant_username from deviant_usernames where deviant_username is not null"
    with env.BotSessionLocal() as db:
        da_usernames = db.scalars(
            select(users.Hubbers.deviant_username)
            .where(
                users.Hubbers.deviant_username is not None
            ).order_by(
                sqrandom()
            )
        ).all()
        return da_usernames[:num]


def get_n_random_creations(num):
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


def hubber_has_new_creations(username, decoded_results) -> bool:
    cache_entry = user_last_cache_update(username)
    needs_update = (datetime.date.today() - cache_entry.last_updated) >= datetime.timedelta(days=7)
    for date in decoded_results:
        if datetime.date.fromtimestamp(int(date['published_time'])) >= cache_entry.last_updated or needs_update:
            return True
    return False


def user_last_cache_update(username) -> cache.Cache.last_updated:
    user_id_row = fetch_hubber_row_id(username)
    if not user_id_row:
        return None
    with env.BotSessionLocal() as db:
        # query = f"""SELECT last_updated from cache_updated_date where deviant_row_id = {user_id_row}"""
        cache_entry = db.scalars(select(cache.Cache).filter_by(deviant_row_id=user_id_row)).first()
    return cache_entry


def fetch_hubber_row_id(username: str | int):
    # query = f"Select id from deviant_usernames where lower(deviant_username) = '{username.lower()}' " if \
    #     isinstance(username, str) else \
    #     f"Select id from deviant_usernames where id = {username} "
    with env.BotSessionLocal() as db:
        result = db.scalars(
            select(users.Hubbers.id).where(
                func.lower(users.Hubbers.deviant_username) == username.lower()
            )
        ).first()
        if result is None:
            return username
        return result


def initial_add_to_cache(results, row_id):
    with env.BotSessionLocal() as db:
        for result in results:
            clean_snippet, clean_title, formatted_dt, tags = format_cache_result(result)
            # query = f"INSERT INTO deviations (deviant_user_row, url, src_image, src_snippet, title, favs, tags, " \
            #     f"date_created, is_mature) VALUES {values_list} ON CONFLICT (url) DO UPDATE set favs=excluded.favs, "
            #     f"title=excluded.title, tags=excluded.tags, is_mature=excluded.is_mature, "
            #     f"src_image=excluded.src_image, src_snippet=excluded.src_snippet"
            in_cache = db.scalars(select(creations.Creations).where(
                creations.Creations.url == result['url']
            )).first()
            if in_cache:

                in_cache.favorites = result['stats']['favourites']
            else:
                deviation_insert = creations.Creations(
                    deviant_user_row=row_id, url=result['url'], src_image=result['src_image'],
                    src_snippet=clean_snippet,
                    title=clean_title, favs=result['stats']['favourites'], tags=tags, date_created=formatted_dt,
                    is_mature=result['is_mature']
                )
                db.add(deviation_insert)
        db.commit()
    update_da_cache(row_id)


def update_da_cache(row_id):
    # query = (f"INSERT INTO cache_updated_date (deviant_row_id) VALUES ({row_id}) ON CONFLICT "
    #          f"(deviant_row_id) DO UPDATE SET last_updated = now()")
    with env.BotSessionLocal() as db:
        in_cache = db.scalars(select(cache.Cache).where(
            cache.Cache.deviant_row_id == row_id
        )).first()
        if in_cache:
            in_cache.last_updated = now()
        else:
            db.add(cache.Cache(deviant_row_id=row_id))
        db.commit()


def get_random_creations_by_hubber(deviant_user_row, limit):
    with env.BotSessionLocal() as db:
        results = db.scalars(
            select(creations.Creations)
            .filter_by(deviant_user_row=deviant_user_row)
            .order_by(sqrandom())
            .limit(limit)
        ).all()
        return results


def get_n_random_creation_by_many_hubbers(limit):
    with env.BotSessionLocal() as db:
        subquery = select(
            users.Hubbers.id
        ).order_by(func.random()).limit(limit).subquery()
        results = db.scalars(
            select(creations.Creations)
            .filter(
                creations.Creations.deviant_user_row.in_(
                    select(subquery)
                )
            )
            .distinct(creations.Creations.deviant_user_row)
        ).all()
        return results, _generate_links(results, limit)


def fetch_n_random_hubber_ids(num):
    with env.BotSessionLocal() as db:
        return db.scalars(
            select(users.Hubbers.id)
            .order_by(sqrandom())
            .limit(num)
        ).all()
