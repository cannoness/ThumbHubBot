HUBCOINS_DESCRIPTION = f'''Documentation for command "!hubcoins"
`!hubcoins`
See how many hubcoins you currently have."

`!hubcoins @user`
See how many hubcoins another user currently has.'''

HUBCOINS_FOOTER = "For information on spending hubcoins, see help for 'spend-hubcoins'"

SPEND_HUBCOINS_DESCRIPTION = f"""Documentation for command "!spend-hubcoins"
`!spend-hubcoins reason amount`
Basic structure for spending hubcoins. Amount is not necessary for reasons other than donating or redeeming XP.

`Rewards`
**XP**: Trade one hubcoin for one rank XP. Please specify the amount.
**Donate**: Donate hubcoins to another member. Please specify the amount.
**Color; 100**: Change the color of your name in the server for a week! Please specify a color name in place of amount. 
[Color List](https://discord.com/channels/697493100519620640/712139217710612492/1133543297823019149).
**Feature; 100**: Purchase a feature (one art piece) in the ThumbHub Journal.
**VIP; 500**: Purchase a week of VIP status. VIP status has all the perks of FT and more!
**Spotlight 1000**: Purchase a full spotlight in ThumbHub! Reminder, there are a few CV's who follow our group."""

SPEND_HUBCOINS_FOOTER = ("Role colors are automatically assigned, but for other purchases, a Mod will DM to "
                         "confirm details with you.")

ART_DESCRIPTION = f"""Documentation for command '!art'

`!art deviantart-username`
Pulls the first n number of deviations from the 'All' gallery of the provided deviantart account username.

`!art deviantart-username rnd`
Pulls n random deviations for the given deviantart user.

`!art deviantart-username +offset`
Pulls n deviations, starting with the offset number given. E.g. +1 would skip the first deviation in the gallery.

`!art deviant-username limit`
Shows the only the number of deviations requested by limit. E.g. 1 would only show 1 deviation.

`!art deviant-username #tag`
Gets artwork with the given tag name.

`!art deviant-username pop`
Shows popular deviations.*

`!art deviant-username old`
Shows old deviations.*

`!art deviant-username gallery "Gallery Name"`
Shows the first five images in a gallery folder. Gallery name is no longer case sensitive.

The commands can be combined in various ways, but limit MUST be last. 
Examples:
`!art user pop rnd +5 1`
Shows the fifth random popular deviation from the user."""

ART_FOOTER = "*Only works if the user is saved the ThumbHub store (see command store-outside-da-name)"
