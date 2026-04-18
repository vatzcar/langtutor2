import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/language_provider.dart';
import '../../providers/session_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/persona_avatar.dart';
import '../../widgets/top_info_bar.dart';

/// Hub screen for starting practice sessions (voice, video, or chat).
class PracticeHubScreen extends ConsumerWidget {
  const PracticeHubScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final selectedLang = ref.watch(selectedLanguageProvider);
    final plan = ref.watch(currentPlanProvider);

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
        backgroundColor: AppColors.bgPractice,
        child: SafeArea(
          child: Column(
            children: [
              TopInfoBar(
                languageFlag: flagUrl,
                cefrLevel: cefrLevel,
                progressPercent: progress,
                planName: planName,
              ),

              const SizedBox(height: 24),

              // Title
              Text(
                'PRACTICE HUB',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      letterSpacing: 3,
                    ),
              ),

              const SizedBox(height: 28),

              const PersonaAvatar(size: 180, showBorder: true),

              const Spacer(),

              // Voice + Video row
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Row(
                  children: [
                    Expanded(
                      child: _SessionButton(
                        icon: Icons.phone_rounded,
                        label: 'VOICE',
                        enabled: hasVoice,
                        onTap: () => _startSession(
                            ref, context, 'voice', 'practice'),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _SessionButton(
                        icon: Icons.videocam_rounded,
                        label: 'VIDEO',
                        enabled: hasVideo,
                        onTap: () => _startSession(
                            ref, context, 'video', 'practice'),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Chat button
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: SizedBox(
                  width: double.infinity,
                  child: _SessionButton(
                    icon: Icons.chat_rounded,
                    label: 'CHAT',
                    enabled: true,
                    onTap: () =>
                        _startSession(ref, context, 'chat', 'practice'),
                  ),
                ),
              ),

              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _startSession(
    WidgetRef ref,
    BuildContext context,
    String type,
    String mode,
  ) async {
    await ref.read(sessionProvider.notifier).startSession(
          type: type,
          mode: mode,
        );
    if (!context.mounted) return;

    switch (type) {
      case 'voice':
        context.push('/learning/voice', extra: mode);
      case 'video':
        context.push('/learning/video', extra: mode);
      case 'chat':
        context.push('/learning/chat', extra: mode);
    }
  }

}

// ---------------------------------------------------------------------------
// Session button
// ---------------------------------------------------------------------------

class _SessionButton extends StatelessWidget {
  const _SessionButton({
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
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: enabled ? AppColors.primary : AppColors.disabledBg,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white, size: 22),
            const SizedBox(width: 8),
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
