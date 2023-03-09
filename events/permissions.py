import nextcord


class SCM:
    class Config:
        class Default(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    add_reactions=False,
                    read_messages=False,
                    view_channel=False,
                    send_messages=False,
                    send_tts_messages=False,
                    manage_messages=False,
                    embed_links=False,
                    attach_files=False,
                    read_message_history=False,
                    mention_everyone=False,
                    external_emojis=False,
                    use_external_emojis=False,
                    use_slash_commands=False,
                    create_public_threads=False,
                    create_private_threads=False,
                    manage_threads=False,
                    external_stickers=False,
                    use_external_stickers=False,
                    send_messages_in_threads=False
                )

        class Allowed(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    read_messages=True,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    mention_everyone=True,
                    use_slash_commands=True,
                )

    class Text:
        class Default(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    read_messages=False,
                    view_channel=False,
                    send_messages=False,
                    read_message_history=False
                )

        class Allowed(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    read_messages=True,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        class Blocked(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    read_messages=False,
                    view_channel=False,
                    send_messages=False,
                    read_message_history=False
                )

    class Voice:
        class Default(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    connect=False
                )

        class Allowed(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    connect=True
                )

        class Blocked(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    connect=False
                )

    class Queue:
        class Default(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    stream=False,
                    view_channel=True,
                    connect=True,
                    speak=False,
                    start_embedded_activities=False
                )

        class Blocked(nextcord.PermissionOverwrite):
            def __init__(self):
                super().__init__(
                    connect=False
                )
