import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/language_provider.dart';
import '../../providers/plan_provider.dart';
import '../../providers/session_provider.dart';
import '../../widgets/persona_avatar.dart';
import '../../widgets/top_info_bar.dart';
import 'language_popup.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final cefrLevel = ref.watch(cefrLevelProvider);
    final plan = ref.watch(currentPlanProvider);

    final cefrText = cefrLevel.whenOrNull(data: (info) => info?.level) ?? '';
    final progress =
        cefrLevel.whenOrNull(data: (info) => info?.progressPercent) ?? 0.0;
    final planName = plan.whenOrNull(data: (p) => p?.name) ?? '';

    final hasVoice =
        plan.whenOrNull(data: (p) => p?.hasVoiceCall) ?? false;
    final hasVideo =
        plan.whenOrNull(data: (p) => p?.hasVideoCall) ?? false;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Column(
            children: [
              const SizedBox(height: 8),

              // Top info bar
              TopInfoBar(
                cefrLevel: cefrText,
                progressPercent: progress.toInt(),
                planName: planName,
                onLanguageTap: () {
                  showDialog(
                    context: context,
                    barrierColor: Colors.black54,
                    builder: (_) => const LanguagePopup(),
                  );
                },
              ),

              const Spacer(),

              // Persona avatar
              const PersonaAvatar(size: 220),

              const Spacer(),

              // Call buttons row
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                decoration: BoxDecoration(
                  color: AppColors.navBg,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Voice call button
                    IconButton(
                      onPressed: hasVoice
                          ? () {
                              ref
                                  .read(sessionProvider.notifier)
                                  .startSession(type: 'voice', mode: 'learning');
                              context.go('/learning/voice',
                                  extra: 'learning');
                            }
                          : null,
                      icon: Icon(
                        Icons.mic,
                        size: 32,
                        color: hasVoice
                            ? Colors.white
                            : AppColors.disabled,
                      ),
                    ),

                    Container(
                      width: 1,
                      height: 32,
                      margin: const EdgeInsets.symmetric(horizontal: 12),
                      color: AppColors.divider,
                    ),

                    // Video call button
                    IconButton(
                      onPressed: hasVideo
                          ? () {
                              ref
                                  .read(sessionProvider.notifier)
                                  .startSession(type: 'video', mode: 'learning');
                              context.go('/learning/video',
                                  extra: 'learning');
                            }
                          : null,
                      icon: Icon(
                        Icons.videocam,
                        size: 32,
                        color: hasVideo
                            ? Colors.white
                            : AppColors.disabled,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // CHAT button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    context.go('/learning/chat');
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.navBg,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: const Text(
                    'CHAT',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
