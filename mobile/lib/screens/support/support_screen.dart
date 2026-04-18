import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../models/session.dart';
import '../../providers/auth_provider.dart';
import '../../providers/language_provider.dart';
import '../../providers/session_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/top_info_bar.dart';

// ---------------------------------------------------------------------------
// Provider: support session history
// ---------------------------------------------------------------------------

final supportHistoryProvider =
    FutureProvider<List<LearningSession>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get(
    '/mobile/sessions',
    queryParameters: {'session_mode': 'support'},
  );
  final items = response.data as List<dynamic>;
  return items
      .map((e) => LearningSession.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ---------------------------------------------------------------------------
// SupportScreen
// ---------------------------------------------------------------------------

class SupportScreen extends ConsumerStatefulWidget {
  const SupportScreen({super.key});

  @override
  ConsumerState<SupportScreen> createState() => _SupportScreenState();
}

class _SupportScreenState extends ConsumerState<SupportScreen>
    with SingleTickerProviderStateMixin {
  bool _showOptions = false;
  late AnimationController _animController;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(1, 0),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOut,
    ));
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  void _toggleOptions() {
    setState(() => _showOptions = !_showOptions);
    if (_showOptions) {
      _animController.forward();
    } else {
      _animController.reverse();
    }
  }

  Future<void> _startSupportSession(
      BuildContext context, String type) async {
    await ref.read(sessionProvider.notifier).startSession(
          type: type,
          mode: 'support',
        );
    if (!context.mounted) return;

    setState(() => _showOptions = false);
    _animController.reverse();

    switch (type) {
      case 'voice':
        context.push('/learning/voice', extra: 'support');
      case 'video':
        context.push('/learning/video', extra: 'support');
      case 'chat':
        context.push('/learning/chat', extra: 'support');
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final selectedLang = ref.watch(selectedLanguageProvider);
    final plan = ref.watch(currentPlanProvider);
    final historyAsync = ref.watch(supportHistoryProvider);

    final cefrLevel =
        selectedLang?['current_cefr_level'] as String? ?? '--';
    final progress =
        (selectedLang?['cefr_progress_percent'] as num?)?.toInt() ?? 0;
    final planName = plan.whenOrNull(data: (p) => p?.name) ?? '';
    final flagUrl = selectedLang?['icon_url'] as String?;

    final hasVoice =
        plan.whenOrNull(data: (p) => p?.hasVoiceCall) ?? false;
    final hasVideo =
        plan.whenOrNull(data: (p) => p?.hasVideoCall) ?? false;

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgSupport,
        child: SafeArea(
          child: Stack(
            children: [
              Column(
                children: [
                  TopInfoBar(
                    languageFlag: flagUrl,
                    cefrLevel: cefrLevel,
                    progressPercent: progress,
                    planName: planName,
                  ),

                  const SizedBox(height: 16),

                  // Support history
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.6),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'SUPPORT HISTORY',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.copyWith(letterSpacing: 2),
                            ),
                            const SizedBox(height: 12),
                            Expanded(
                              child: historyAsync.when(
                                loading: () => const Center(
                                    child: CircularProgressIndicator()),
                                error: (e, _) =>
                                    Center(child: Text('Error: $e')),
                                data: (sessions) => sessions.isEmpty
                                    ? const Center(
                                        child: Text('No support sessions'))
                                    : ListView.builder(
                                        itemCount: sessions.length,
                                        itemBuilder: (_, index) {
                                          final s = sessions[index];
                                          return _SupportSessionCard(
                                              session: s);
                                        },
                                      ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: 80),
                ],
              ),

              // Options menu (slide-in)
              if (_showOptions)
                Positioned(
                  bottom: 90,
                  right: 16,
                  child: SlideTransition(
                    position: _slideAnimation,
                    child: Container(
                      width: 200,
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: AppColors.navBg,
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.15),
                            blurRadius: 12,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          _OptionItem(
                            icon: Icons.videocam_rounded,
                            label: 'VIDEO CALL',
                            enabled: hasVideo,
                            onTap: () =>
                                _startSupportSession(context, 'video'),
                          ),
                          _OptionItem(
                            icon: Icons.phone_rounded,
                            label: 'VOICE CALL',
                            enabled: hasVoice,
                            onTap: () =>
                                _startSupportSession(context, 'voice'),
                          ),
                          _OptionItem(
                            icon: Icons.chat_rounded,
                            label: 'CHAT',
                            enabled: true,
                            onTap: () =>
                                _startSupportSession(context, 'chat'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),

              // FAB
              Positioned(
                bottom: 20,
                right: 16,
                child: GestureDetector(
                  onTap: _toggleOptions,
                  child: Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      color: AppColors.navBg,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.15),
                          blurRadius: 8,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Icon(
                      _showOptions
                          ? Icons.close_rounded
                          : Icons.message_rounded,
                      color: Colors.white,
                      size: 26,
                    ),
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
// Support session card
// ---------------------------------------------------------------------------

class _SupportSessionCard extends StatelessWidget {
  const _SupportSessionCard({required this.session});

  final LearningSession session;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${session.sessionType.toUpperCase()} Session',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  session.startedAt.split('T').first,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right_rounded,
              color: AppColors.textMuted),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Option item
// ---------------------------------------------------------------------------

class _OptionItem extends StatelessWidget {
  const _OptionItem({
    required this.icon,
    required this.label,
    required this.enabled,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(
          children: [
            Icon(
              icon,
              color: enabled ? Colors.white : AppColors.disabled,
              size: 20,
            ),
            const SizedBox(width: 12),
            Text(
              label,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: enabled ? Colors.white : AppColors.disabled,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
