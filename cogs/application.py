# cogs/application.py
import discord
from discord.ext import commands
import config

class ApplicationModal(discord.ui.Modal, title='Анкета в ОПГ Белозерские'):
    nickname = discord.ui.TextInput(label='Никнейм (игровой ник)', placeholder='Максим Нарузов', required=True)
    static_id = discord.ui.TextInput(label='Static ID', placeholder='Например: 12345', required=True)
    source = discord.ui.TextInput(label='Кто пригласил', placeholder='Никнейм игрока или "Нет"', required=True)
    rank = discord.ui.TextInput(label='Текущий ранг (цифрой от 1 до 7)', placeholder='Например: 1', min_length=1, max_length=1, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if self.rank.value not in config.RANKS_DATA:
            await interaction.response.send_message("Ошибка: Ранг должен быть строго цифрой от 1 до 7!", ephemeral=True)
            return

        admin_channel = interaction.client.get_channel(config.ADMIN_CHANNEL_ID)
        if admin_channel is None:
            await interaction.response.send_message("Ошибка: Не удалось найти канал администрации. Проверьте ID.", ephemeral=True)
            return

        embed = discord.Embed(title="⚡ Новая заявка на проверку роли!", color=discord.Color.red())
        embed.add_field(name="Пользователь Discord", value=interaction.user.mention, inline=False)
        embed.add_field(name="Желаемый Никнейм", value=self.nickname.value, inline=True)
        embed.add_field(name="Static ID", value=self.static_id.value, inline=True)
        embed.add_field(name="Кто пригласил", value=self.source.value, inline=False)
        embed.add_field(name="Запрашиваемый ранг", value=f"**{config.RANKS_DATA[self.rank.value]['name']}**", inline=True)
        embed.set_footer(text=f"ID Пользователя: {interaction.user.id}")

        await admin_channel.send(embed=embed, view=AdminApprovalView(user_id=interaction.user.id, user_nickname=self.nickname.value, user_rank=self.rank.value))
        await interaction.response.send_message("Ваша заявка успешно отправлена на проверку старшему составу ОПГ!", ephemeral=True)

class PlayerMenuView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Подать заявку", style=discord.ButtonStyle.danger, custom_id="btn_apply_opg")
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplicationModal())

class AdminApprovalView(discord.ui.View):
    def __init__(self, user_id: int, user_nickname: str, user_rank: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_nickname = user_nickname
        self.user_rank = user_rank 

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success, custom_id="btn_approve")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = guild.get_member(self.user_id)

        if member is None:
            await interaction.followup.send("Игрок вышел с сервера, не могу одобрить.", ephemeral=True)
            return

        rank_info = config.RANKS_DATA[self.user_rank]
        target_role = guild.get_role(rank_info["id"])
        roles_to_add = []
        
        if target_role:
            roles_to_add.append(target_role)
            role_status = f"Основная роль: **{target_role.name}**"
        else:
            role_status = f"Основная роль с ID {rank_info['id']} не найдена!"

        extra_roles_status = []
        for extra_id in config.EXTRA_ROLES_IDS:
            ex_role = guild.get_role(extra_id)
            if ex_role:
                roles_to_add.append(ex_role)
                extra_roles_status.append(ex_role.name)

        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add)
                roles_log = f"✅ {role_status}\n✅ Доп. роли: {', '.join(extra_roles_status)}"
            except discord.Forbidden:
                roles_log = "❌ Ошибка: У бота нет прав на выдачу ролей (Перетащите роль бота НА САМЫЙ ВЕРХ!)"

        formatted_nickname = f"[{self.user_rank}] {self.user_nickname}"
        if len(formatted_nickname) > 32: 
            formatted_nickname = formatted_nickname[:32]

        try:
            await member.edit(nick=formatted_nickname)
            nick_status = f"✅ Ник изменен на: **{formatted_nickname}**"
        except discord.Forbidden:
            nick_status = "❌ Не удалось изменить ник (бот ниже по правам в списке ролей)"

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "🟢 ЗАЯВКА ОДОБРЕНА АДМИНИСТРАЦИЕЙ"
        embed.add_field(name="📝 Аудит проверки", value=f"**Проверил:** {interaction.user.mention}\n**Вердикт:** Принят в ОПГ\n{roles_log}\n{nick_status}", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.followup.send(f"Вы успешно одобрили игрока {member.mention}!", ephemeral=True)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger, custom_id="btn_deny")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.light_gray()
        embed.title = "🔴 ЗАЯВКА ОТКЛОНЕНА AДМИНИСТРАЦИЕЙ"
        embed.add_field(name="📝 Аудит проверки", value=f"**Проверил:** {interaction.user.mention}\n**Вердикт:** Отказ в выдаче ролей.", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.followup.send("Заявка отклонена.", ephemeral=True)

class ApplicationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_menu(self, ctx):
        embed = discord.Embed(
            title="ОПГ <<Белозерские>> | Электронные заявления на масть",
            description="Хочешь продвигаться по мастям и помогать братве? Жми кнопку ниже и заполняй маляву.\n\n"
                        "**Перед подачей приготовь:**\n"
                        "• Свой точный игровой ник\n"
                        "• Твой личный Static ID\n"
                        "• Ник того, кто тебя подтянул в ОПГ\n"
                        "• Твою масть/ранг цифрой (**от 1 до 7**)",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, view=PlayerMenuView())

async def setup(bot):
    await bot.add_cog(ApplicationCog(bot))
