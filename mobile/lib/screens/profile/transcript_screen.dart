import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../models/chat_message.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/persona_avatar.dart';

// ---------------------------------------------------------------------------
// Provider: session transcript
// ---------------------------------------------------------------------------

final transcriptProvider =
    FutureProvider.family<List<ChatMessage>, String>((ref, sessionId) async {
  final apiClient = ref.watch(apiClientProvider);
  final response =
      await apiClient.get('/mobile/sessions/$sessionId/transcript');
  final items = response.data as List<dynamic>;
  return items
      .map((e) => ChatMessage.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ---------------------------------------------------------------------------
// TranscriptScreen
// ---------------------------------------------------------------------------

class TranscriptScreen extends ConsumerWidget {
  const TranscriptScreen({super.key, required this.sessionId});

  final String sessionId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final transcriptAsync = ref.watch(transcriptProvider(sessionId));

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgChat,
        child: SafeArea(
          child: Column(
            children: [
              // Top bar
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 10),
                color: AppColors.navBg,
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back_rounded,
                          color: Colors.white),
                      onPressed: () => context.pop(),
                    ),
                    const PersonaAvatar(size: 36),
                    const SizedBox(width: 10),
                    const Text(
                      'Session Transcript',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),

              // Transcript messages
              Expanded(
                child: transcriptAsync.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (e, _) =>
                      Center(child: Text('Error: $e')),
                  data: (messages) => messages.isEmpty
                      ? const Center(child: Text('No messages'))
                      : ListView.builder(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 8),
                          itemCount: messages.length,
                          itemBuilder: (_, index) {
                            return _TranscriptBubble(
                                message: messages[index]);
                          },
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Transcript bubble (read-only chat bubble)
// ---------------------------------------------------------------------------

class _TranscriptBubble extends StatelessWidget {
  const _TranscriptBubble({required this.message});

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
          style: const TextStyle(
            fontSize: 14,
            color: AppColors.textPrimary,
          ),
        ),
      ),
    );
  }
}
