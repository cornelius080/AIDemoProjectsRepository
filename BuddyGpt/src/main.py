
import flet as ft
import time
import datetime
import asyncio
from typing import List, Optional, Dict
from llm_interface import LLMInterface

####################################################################
# Classes adapted to work with LLMInterface
####################################################################
class Message:
    """Represents a chat message with content, role, and metadata."""
    def __init__(self, content: str, role: str, message_id: Optional[str] = None, is_edited: bool = False, timestamp: Optional[str] = None):
        """
        Initializes a Message object.
        
        Args:
            content: The text content of the message.
            role: The role of the sender (e.g., 'user', 'assistant').
            message_id: Optional unique identifier for the message.
            is_edited: Whether the message has been edited.
            timestamp: Optional ISO format timestamp string.
        """
        self.id = message_id or f"msg_{datetime.datetime.now().timestamp()}"
        self.content = content
        self.role = role

        # We try to parse timestamp if string, else now
        if isinstance(timestamp, str):
            try:
                self.timestamp = datetime.datetime.fromisoformat(timestamp)
            except:
                self.timestamp = datetime.datetime.now()
        else:
            self.timestamp = datetime.datetime.now()
        self.is_edited = is_edited

class ChatApp:
    """Core application logic for managing the chat and LLM interaction."""
    def __init__(self, page: ft.Page):
        """
        Initializes the ChatApp.
        
        Args:
            page: The Flet Page object.
        """
        self.page = page
        # Initialize LLM Interface
        self.llm = LLMInterface()
        self.llm.setup_langsmith_tracing()
        # You might want to expose model config to UI settings in future
        self.llm.initialize_model() 
        # Don't create agent yet, wait for async init
        self.current_session = "chat_default"
        self.ensure_session()

    async def initialize(self):
        """Asynchronously initializes database connection and the agent."""
        await self.llm.initialize_memory()
        # model is initialized here if key is available
        if self.llm.initialize_model():
            self.llm.create_agent_with_memory()

    def ensure_session(self):
        """Ensures that a session ID is set, creating a new one if necessary."""
        if not self.current_session:
            self.new_session()

    async def get_messages(self) -> List[Message]:
        """
        Retrieves messages from LLM interface and converts them to Message objects.
        
        Returns:
            List of Message objects representing the conversation history.
        """
        raw_messages = await self.llm.get_conversation_history(self.current_session)
        msgs = []
        for m in raw_messages:
            # Map LangChain message types to roles
            role = "user" if m.type == "human" else "assistant"
            # Attempt to find id and timestamp if available in metadata, else generate/mock
            msg_id = getattr(m, 'id', None)
            
            msgs.append(Message(
                content=m.content, 
                role=role, 
                message_id=msg_id,
                # We don't have is_edited in standard LangChain msg usually
                is_edited=False 
            ))
        return msgs

    def new_session(self):
        """Generates a new session ID based on the current timestamp."""
        self.current_session = f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def get_saved_conversations(self) -> List[str]:
        """
        Retrieves a list of saved conversation session IDs.
        
        Returns:
            Sorted list of session IDs.
        """
        # Use the async helper we added to LLMInterface
        threads = await self.llm.get_saved_thread_ids()
        if not threads:
             return [self.current_session]
        return sorted(threads, reverse=True)

    async def get_first_message(self, session_name: str) -> str:
        """
        Retrieves the first user message of a session to use as a title.
        
        Args:
            session_name: The session ID.
            
        Returns:
            The content of the first human message or 'New Chat' if none found.
        """
        history = await self.llm.get_conversation_history(session_name)
        for m in history:
            if m.type == "human":
                return m.content
        return "New Chat"

    def load_messages(self, session_name: Optional[str] = None):
        """
        Sets the current session name.
        
        Args:
            session_name: Optional session ID to load.
        """
        if session_name:
            self.current_session = session_name

    async def process_user_message(self, content: str):
        """
        Sends a user message to the LLM agent.
        
        Args:
            content: The user's message content.
        """
        await self.llm.ainvoke_agent(self.current_session, content)


####################################################################
# Main Application
####################################################################
async def main(page: ft.Page):
    """
    Main entry point for the BuddyGPT Flet application.
    Sets up the UI, event handlers, and initializes the ChatApp.
    """
    ################  
    # Event handlers
    ################
    async def update_message_list(optimistic_messages: List[Message] = []):
        """
        Updates the UI message list by fetching the latest messages or using optimistic ones.
        
        Args:
            optimistic_messages: Temporary messages to display before DB sync.
        """
        message_list.controls.clear()
        # Fetch latest messages from the LLM-backed app (Async)
        messages = await chat_app.get_messages()
        
        # Add any temporary/optimistic messages to the view
        if optimistic_messages:
            messages.extend(optimistic_messages)
        
        for message in messages:
            message_col = create_message_control(message)
            message_list.controls.append(message_col)
            
        update_header_layout(len(messages))
        page.update()

    def create_message_control(message: Message):
        """
        Creates a UI control for a single message.
        
        Args:
            message: The Message object.
            
        Returns:
            A Flet Column containing the message UI.
        """
        def on_hover(e):
            if not e.control.page:
                return
            e.control.content.controls[0].visible = not e.control.content.controls[0].visible
            e.control.update()

        def copy_on_click(e, m):
            page.set_clipboard(m.content)
            e.control.icon = ft.Icons.CHECK
            e.control.update()
            time.sleep(0.5) # subtle feedback
            e.control.icon = ft.Icons.CONTENT_COPY
            e.control.update()

        copy_button = ft.IconButton(
            icon=ft.Icons.CONTENT_COPY,
            icon_color = ft.Colors.WHITE,
            icon_size=12,
            tooltip="Copy",
            on_click=lambda e, m=message: copy_on_click(e, m)
        )

        action_row = ft.Row(
            [copy_button,],
            visible=False,
            spacing=1,
            width=125,
        )
        
        content_text = ft.Text(
            message.content,
            size=16,
            color=ft.Colors.WHITE,
            text_align=ft.TextAlign.JUSTIFY if message.role == "user" else ft.TextAlign.LEFT,
        )

        # Create message container
        message_container = ft.Container(
            content=ft.Column(
                [
                    action_row,
                    ft.Row(
                        [
                            ft.Text(
                                f"On {message.timestamp.strftime('%Y-%m-%d  %H:%M:%S')} {'user wrote:' if message.role == 'user' else 'assistant replied:'}",
                                size=10,
                                color=ft.Colors.WHITE70,
                            ),
                        ], 
                        alignment=ft.MainAxisAlignment.END
                    ),
                    content_text,
                    ft.Text(
                        "(edited)" if message.is_edited else "",
                        size=12,
                        color=ft.Colors.GREY_800,
                        visible=message.is_edited
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                tight=True, 
            ),
            bgcolor="#321C64" if message.role == "user" else "#200F49",
            border_radius=20,
            border=ft.border.all(2, "#952BB9"),
            padding=10,
            expand=1,
            on_hover=on_hover,                
        )
        
        if message.role == "user":
            message_row = ft.Row([ft.Container(expand=1), message_container])
        else:
            message_row = ft.Row([message_container])
        
        message_col = ft.Column([message_row], spacing=1)
        
        if message.role != "user":
            message_col.controls.append(ft.Container(height=40))
            
        # Store a reference to the text control for easy updates during streaming
        message_col.content_text = content_text
        return message_col

    def update_header_layout(message_count: int):
        """
        Dynamically adjusts the header layout based on the number of messages.
        
        Args:
            message_count: Number of messages in the current view.
        """
        # Dynamic header adjustment based on message count
        if message_count > 4:
            # Move to top-left
            row_heading.alignment = ft.MainAxisAlignment.START
            row_heading.top = 10
            row_heading.left = 10
            row_heading.right = None
            
            avatar_image.height = 40
            avatar_image.width = 40
            heading_text.theme_style = ft.TextThemeStyle.HEADLINE_LARGE
            
            # Reduce spacer to pull chat up
            spacer_container.height = 10
        else:
            # Center on page
            row_heading.alignment = ft.MainAxisAlignment.CENTER
            row_heading.top = 20
            row_heading.left = 0
            row_heading.right = 0
            
            avatar_image.height = 60
            avatar_image.width = 60
            heading_text.theme_style = ft.TextThemeStyle.DISPLAY_MEDIUM
            
            # Increase spacer to push chat down below the floating header
            spacer_container.height = 90

    async def send_message(e):
        """Handles the send message event, including optimistic updates and streaming."""
        if not input_field.value.strip():
            return
        
        user_text = input_field.value
        input_field.value = ""
        
        # 1. Show user message immediately (optimistic)
        user_msg = Message(content=user_text, role="user")
        user_control = create_message_control(user_msg)
        message_list.controls.append(user_control)
        
        # 2. Show assistant message placeholder (empty initially)
        assistant_msg = Message(content="", role="assistant")
        assistant_control = create_message_control(assistant_msg)
        message_list.controls.append(assistant_control)
        
        page.update()
        
        # User feedback: Show loading spinner in suffix
        original_icon = input_field.suffix_icon
        input_field.suffix_icon = ft.Container(
            content=ft.ProgressRing(width=20, height=20, color=ft.Colors.WHITE),
            padding=10,
        )
        input_field.focus()
        page.update()
        
        full_content = ""
        try:
            # 3. Stream from LLMInterface
            async for token in chat_app.llm.astream_agent(chat_app.current_session, user_text):
                full_content += token
                assistant_control.content_text.value = full_content
                # Update UI
                page.update()
            
            # Update header if threshold reached
            messages_count = len(await chat_app.get_messages()) + 2 # approximately
            update_header_layout(messages_count)
            
        except Exception as err:
            print(f"LLM Streaming Error: {err}")
            assistant_control.content_text.value += f"\n[Error: {err}]"
        finally:
            # Restore send button
            input_field.suffix_icon = original_icon
            
        # Final refresh to ensure everything is synced with DB
        await update_message_list()
        await update_conversations_list()
        input_field.focus()
        page.update()

    def show_settings_dialog(e=None):
        """Displays the settings dialog for API keys."""
        api_key_field = ft.TextField(
            label="Hugging Face API Token",
            password=True,
            can_reveal_password=True,
            value=chat_app.llm.load_api_key() or "",
            border_color=ft.Colors.WHITE,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            label_style=ft.TextStyle(color=ft.Colors.WHITE70),
        )

        langsmith_key_field = ft.TextField(
            label="LangSmith API Key (Optional)",
            password=True,
            can_reveal_password=True,
            value=chat_app.llm.load_api_key("LANGSMITH_API_KEY") or "",
            border_color=ft.Colors.WHITE,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            label_style=ft.TextStyle(color=ft.Colors.WHITE70),
        )

        async def save_settings(e):
            # Save Hugging Face token
            if api_key_field.value.strip():
                chat_app.llm.save_api_key(api_key_field.value.strip())
            
            # Save LangSmith key (always save what's in the field, even if empty, to allow clearing it)
            chat_app.llm.save_api_key(langsmith_key_field.value.strip(), "LANGSMITH_API_KEY")
            
            # Re-trigger LangSmith tracing setup (reads from .env)
            chat_app.llm.setup_langsmith_tracing()

            # Close dialog
            page.close(settings_dialog)
            
            # Re-initialize the model and agent
            if chat_app.llm.initialize_model():
                chat_app.llm.create_agent_with_memory()
                # Update UI
                await update_message_list()
                page.snack_bar = ft.SnackBar(ft.Text("Settings saved and model initialized!"))
                page.snack_bar.open = True
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error initializing model with provided token.", color=ft.Colors.RED))
                page.snack_bar.open = True
            page.update()

        settings_dialog = ft.AlertDialog(
            title=ft.Text("Settings", color=ft.Colors.WHITE),
            content=ft.Column([
                ft.Text("Enter your API Tokens to configure BuddyGPT.", color=ft.Colors.WHITE70),
                api_key_field,
                langsmith_key_field,
            ], tight=True),
            actions=[
                ft.TextButton("Save", on_click=save_settings),
                ft.TextButton("Cancel", on_click=lambda _: page.close(settings_dialog)),
            ],
            bgcolor="#200F49",
        )
        page.open(settings_dialog)

    def show_about_dialog(e):
        """Displays the 'About' dialog."""
        about_dialog = ft.AlertDialog(
            title=ft.Text("About BuddyGPT", color=ft.Colors.WHITE),
            content=ft.Text(
                "This a ChatGPT alternative based on the open source Hugging Face model SmolLM3-3B.\nYou can have multiple conversations ad retrieve them in the history list. Enjoy!!",
                color=ft.Colors.WHITE
            ),
            bgcolor="#200F49",
        )
        page.open(about_dialog)

    async def update_conversations_list():
        """Updates the conversation history list in the UI."""
        history_column.controls.clear()
        history_column.horizontal_alignment = ft.CrossAxisAlignment.START
        sessions = await chat_app.get_saved_conversations()
        
        for session in sessions:
            first_msg = await chat_app.get_first_message(session)
            # Truncate label if long
            label_text = (first_msg[:27] + "...") if len(first_msg) > 30 else first_msg
            
            # Check if this is the current active session
            is_active = session == chat_app.current_session
            
            def create_click_handler(s):
                async def handler(e):
                    await on_conversation_click(s)
                return handler
            
            history_column.controls.append(
                ft.TextButton(
                    content=ft.Text(
                        label_text, 
                        color=ft.Colors.WHITE if is_active else ft.Colors.WHITE70, 
                        italic=not is_active,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL
                    ),
                    on_click=create_click_handler(session),
                    tooltip=first_msg,
                    style=ft.ButtonStyle(
                        padding=ft.padding.only(left=10, right=10),
                        alignment=ft.alignment.center_left,
                        bgcolor=ft.Colors.WHITE10 if is_active else ft.Colors.TRANSPARENT,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                )
            )
        page.update()

    async def on_conversation_click(session_name):
        """Handles clicking on a conversation from the history list."""
        chat_app.load_messages(session_name)
        await update_message_list()
        await update_conversations_list() # Update highlighting
        page.update()

    async def start_new_chat(e):
        """Starts a fresh chat session."""
        chat_app.new_session()
        await update_message_list()
        await update_conversations_list() # Reset highlights
        page.update()
        
    ################
    # Page configuration
    ################   
    page.title = "BuddyGPT"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.maximized = True
    page.padding = 0

    # Initialize the chat app
    chat_app = ChatApp(page)
    # Async initialize memory
    await chat_app.initialize()
    
    # Store the currently edited message ID
    current_editing_message_id = None   
     
    ################
    # UI Controls    
    ################
    btn_settings = ft.IconButton(
        icon=ft.Icons.SETTINGS,
        icon_color=ft.Colors.WHITE,
        icon_size=24,
        tooltip="Settings",
        bottom=10,
        right=10,
        on_click=show_settings_dialog,
    )
    btn_help = ft.IconButton(
        icon=ft.Icons.HELP_OUTLINE,
        icon_color=ft.Colors.WHITE,
        icon_size=24,
        tooltip="About",
        top=10,
        right=10,
        on_click=show_about_dialog,
    )
    btn_new_chat = ft.IconButton(
        icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
        icon_color=ft.Colors.WHITE,
        icon_size=24,
        tooltip="New chat",
        top=10,
        right=55,
        on_click=start_new_chat,
    )
    avatar_image = ft.Image(src="logo.png", height=60, width=60, border_radius=30,)
    heading_text = ft.Text("BuddyGPT", color=ft.Colors.WHITE, theme_style=ft.TextThemeStyle.DISPLAY_MEDIUM)
    row_heading = ft.Row(
        [
            avatar_image,
            heading_text,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    
    # Placeholder to reserve space in the column when header is centered
    spacer_container = ft.Container(height=90)
    message_list = ft.ListView(
        expand=True,
        spacing=10,
        padding=0,
        auto_scroll=True,
    )
    msg_container = ft.Container(
        expand=True,
        height=600,
        content = message_list,
    )
    input_field = ft.TextField(
        border_color=ft.Colors.WHITE,
        border_width=3,
        border_radius=ft.border_radius.all(10),
        cursor_color=ft.Colors.WHITE,
        text_style = ft.TextStyle(color=ft.Colors.WHITE),
        min_lines=3,
        max_lines=3,
        bgcolor="#321C64",
        suffix_icon=ft.IconButton(
            ft.Icons.SEND_ROUNDED, 
            icon_color=ft.Colors.WHITE, 
            icon_size=24,
            on_click=send_message
        ),
    )
    row_warning = ft.Row(
        [
            ft.Text("BuddyGPT can make mistakes. Make sure to verify important information.", color=ft.Colors.WHITE, theme_style=ft.TextThemeStyle.BODY_SMALL),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    history_column = ft.Column(
        spacing=5,
        scroll=ft.ScrollMode.AUTO,
    )
    
    history_container = ft.Container(
        content=history_column,
        left=10,
        top=100,
        width=210,
        bottom=50,
    )
  
    ################
    # Assemble the main layout
    ################
    page.add(
        ft.Container(
            gradient=ft.LinearGradient(
                begin=ft.alignment.bottom_left,
                end=ft.Alignment(-0.1, 0),
                colors=["#712291", "#3A3474"],
            ),
            expand=True,
            content=ft.Stack(
                controls=[
                    ft.Container(
                        padding=ft.padding.only(top=10, bottom=10, left=250, right=250),
                        content=ft.Column(
                            [
                                spacer_container,
                                msg_container, 
                                input_field,
                                ft.Container(height=2), 
                                row_warning,
                            ],
                            spacing=0,
                        ),
                    ),
                    row_heading,
                    history_container,
                    btn_settings,
                    btn_new_chat,
                    btn_help,
                ],
            ),
        ),
    )
    async def cleanup_on_disconnect(e):
        await chat_app.llm.close()

    page.on_disconnect = cleanup_on_disconnect

    # Load initial messages and conversation list
    await update_message_list()
    await update_conversations_list()

    # Initial check for API Key
    if not chat_app.llm.load_api_key():
        show_settings_dialog()

ft.app(target=main, assets_dir="assets")