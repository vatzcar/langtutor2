import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/language_provider.dart';
import '../../models/chat_message.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../widgets/bubble_background.dart';

// ---------------------------------------------------------------------------
// Chat provider (stubbed -- will be replaced by WebSocket/REST provider)
// ---------------------------------------------------------------------------

class ChatState {
  final List<ChatMessage> messages;
  final bool isLimitReached;
  final bool isSending;

  const ChatState({
    this.messages = const [],
    this.isLimitReached = false,
    this.isSending = false,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isLimitReached,
    bool? isSending,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isLimitReached: isLimitReached ?? this.isLimitReached,
      isSending: isSending ?? this.isSending,
    );
  }
}

class ChatNotifier extends StateNotifier<ChatState> {
  final dynamic Function() _getApiClient;

  ChatNotifier(this._getApiClient) : super(const ChatState());

  Future<void> sendMessage(String content) async {
    if (content.trim().isEmpty || state.isLimitReached) return;

    state = state.copyWith(isSending: true);

    final userMsg = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      sender: 'user',
      content: content.trim(),
      createdAt: DateTime.now().toIso8601String(),
    );

    state = state.copyWith(messages: [...state.messages, userMsg]);

    try {
      final api = _getApiClient();
      final response = await api.post(
        '/mobile/chat/send',
        data: {'content': content.trim()},
      );
      final data = response.data as Map<String, dynamic>;
      final reply = ChatMessage.fromJson(data);
      state = state.copyWith(
        messages: [...state.messages, reply],
        isSending: false,
      );
    } catch (_) {
      state = state.copyWith(isSending: false);
    }
  }
}

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>((ref) {
  return ChatNotifier(() => ref.read(apiClientProvider));
});

// ---------------------------------------------------------------------------
// ChatScreen
// ---------------------------------------------------------------------------

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key, this.mode = 'learning'});

  final String mode;

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _textController = TextEditingController();
  bool _isAtBottom = true;
  bool _hasNewUnread = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _textController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final atBottom = _scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 40;
    if (atBottom != _isAtBottom) {
      setState(() {
        _isAtBottom = atBottom;
        if (atBottom) _hasNewUnread = false;
      });
    }
  }

  void _scrollToBottom() {
    _scrollController.animateTo(
      _scrollController.position.maxScrollExtent,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOut,
    );
    setState(() {
      _isAtBottom = true;
      _hasNewUnread = false;
    });
  }

  void _sendMessage() {
    final text = _textController.text;
    if (text.trim().isEmpty) return;
    ref.read(chatProvider.notifier).sendMessage(text);
    _textController.clear();
    // Scroll to bottom after frame renders.
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
  }

  void _navigateTab(BuildContext context, int index) {
    const routes = ['/home', '/practice', '/profile', '/support'];
    if (index < routes.length) context.go(routes[index]);
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
    final selectedLang = ref.watch(selectedLanguageProvider);

    // Mark new unread when messages arrive and user isn't at bottom.
    ref.listen<ChatState>(chatProvider, (prev, next) {
      if (!_isAtBottom &&
          next.messages.length > (prev?.messages.length ?? 0)) {
        setState(() => _hasNewUnread = true);

        // Auto-mark as read after 5 seconds if still visible.
        Timer(const Duration(seconds: 5), () {
          if (mounted && _hasNewUnread) {
            setState(() => _hasNewUnread = false);
          }
        });
      }
    });

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgChat,
        child: SafeArea(
          child: Column(
            children: [
              // Top bar
              _buildTopBar(selectedLang),

              // Messages
              Expanded(
                child: Stack(
                  children: [
                    ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 8),
                      itemCount: chatState.messages.length,
                      itemBuilder: (_, index) {
                        final msg = chatState.messages[index];
                        return _ChatBubble(message: msg);
                      },
                    ),

                    // New-message indicator
                    if (!_isAtBottom && _hasNewUnread)
                      Positioned(
                        bottom: 12,
                        right: 16,
                        child: GestureDetector(
                          onTap: _scrollToBottom,
                          child: Container(
                            width: 36,
                            height: 36,
                            decoration: const BoxDecoration(
                              color: AppColors.success,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.arrow_downward_rounded,
                              color: Colors.white,
                              size: 20,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),

              // Input area
              _buildInputArea(chatState),
            ],
          ),
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: 0,
        onTap: (i) => _navigateTab(context, i),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Sub-widgets
  // ---------------------------------------------------------------------------

  Widget _buildTopBar(Map<String, dynamic>? lang) {
    final flagUrl = lang?['icon_url'] as String?;
    final langName = lang?['name'] as String? ?? 'Language';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      color: AppColors.navBg,
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
            onPressed: () => context.pop(),
          ),
          CircleAvatar(
            radius: 18,
            backgroundColor: AppColors.disabledBg,
            child: const Icon(Icons.person, size: 20, color: AppColors.disabled),
          ),
          const SizedBox(width: 10),
          if (flagUrl != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: Image.network(flagUrl, width: 24, height: 16,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const SizedBox.shrink()),
            ),
          const SizedBox(width: 6),
          Text(
            langName,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInputArea(ChatState chatState) {
    final disabled = chatState.isLimitReached;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      color: Colors.white,
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              enabled: !disabled,
              minLines: 1,
              maxLines: 3,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _sendMessage(),
              decoration: InputDecoration(
                hintText: disabled ? 'Limit reached' : 'Type a message...',
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                filled: false,
              ),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: disabled ? null : _sendMessage,
            child: Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: disabled ? AppColors.disabledBg : AppColors.primary,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.send_rounded,
                  color: Colors.white, size: 20),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Chat bubble
// ---------------------------------------------------------------------------

class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.sender == 'user';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints:
            BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: isUser
              ? AppColors.primary.withValues(alpha: 0.15)
              : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Text(
          message.content,
          style: TextStyle(
            fontSize: 14,
            color: isUser ? AppColors.textPrimary : AppColors.textPrimary,
          ),
        ),
      ),
    );
  }
}
