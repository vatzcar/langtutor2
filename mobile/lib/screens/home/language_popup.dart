import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../providers/language_provider.dart';

class LanguagePopup extends ConsumerWidget {
  const LanguagePopup({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userLanguages = ref.watch(userLanguagesProvider);
    final allLanguages = ref.watch(languagesProvider);
    final selectedLanguageId = ref.watch(selectedLanguageIdProvider);

    return GestureDetector(
      onTap: () => Navigator.of(context).pop(),
      child: Material(
        color: Colors.transparent,
        child: Center(
          child: GestureDetector(
            onTap: () {}, // Prevent dismiss when tapping inside
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 24),
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.navBg.withOpacity(0.95),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Currently learning languages
                  userLanguages.when(
                    data: (languages) {
                      return allLanguages.when(
                        data: (allLangs) {
                          // Filter to languages the user is learning
                          final learningIds = languages
                              .map((ul) => ul['language_id'] as String)
                              .toSet();
                          final learningLangs = allLangs
                              .where((l) => learningIds.contains(l.id))
                              .toList();

                          return Wrap(
                            spacing: 12,
                            runSpacing: 12,
                            children: learningLangs.map((lang) {
                              final isSelected =
                                  lang.id == selectedLanguageId;
                              return GestureDetector(
                                onTap: () {
                                  ref
                                      .read(selectedLanguageIdProvider
                                          .notifier)
                                      .state = lang.id;
                                  Navigator.of(context).pop();
                                },
                                child: _LanguageFlag(
                                  name: lang.name,
                                  iconUrl: lang.iconUrl,
                                  isSelected: isSelected,
                                ),
                              );
                            }).toList(),
                          );
                        },
                        loading: () => const Center(
                          child: CircularProgressIndicator(),
                        ),
                        error: (_, __) => const SizedBox.shrink(),
                      );
                    },
                    loading: () =>
                        const Center(child: CircularProgressIndicator()),
                    error: (_, __) => const SizedBox.shrink(),
                  ),

                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Divider(color: AppColors.divider, height: 1),
                  ),

                  // Learn A New Language title
                  Text(
                    'Learn A New Language',
                    style: Theme.of(context)
                        .textTheme
                        .headlineSmall
                        ?.copyWith(color: Colors.white),
                  ),
                  const SizedBox(height: 12),

                  // Available languages (not yet learning)
                  allLanguages.when(
                    data: (allLangs) {
                      return userLanguages.when(
                        data: (userLangs) {
                          final learningIds = userLangs
                              .map((ul) => ul['language_id'] as String)
                              .toSet();
                          final available = allLangs
                              .where((l) =>
                                  !learningIds.contains(l.id) && l.isActive)
                              .toList();

                          if (available.isEmpty) {
                            return Text(
                              'No more languages available',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(color: AppColors.textMuted),
                            );
                          }

                          return Wrap(
                            spacing: 12,
                            runSpacing: 12,
                            children: available.map((lang) {
                              return GestureDetector(
                                onTap: () {
                                  Navigator.of(context).pop();
                                  context.go('/onboarding/call',
                                      extra: lang.id);
                                },
                                child: _LanguageFlag(
                                  name: lang.name,
                                  iconUrl: lang.iconUrl,
                                  isSelected: false,
                                ),
                              );
                            }).toList(),
                          );
                        },
                        loading: () => const Center(
                          child: CircularProgressIndicator(),
                        ),
                        error: (_, __) => const SizedBox.shrink(),
                      );
                    },
                    loading: () =>
                        const Center(child: CircularProgressIndicator()),
                    error: (_, __) => const SizedBox.shrink(),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LanguageFlag extends StatelessWidget {
  final String name;
  final String? iconUrl;
  final bool isSelected;

  const _LanguageFlag({
    required this.name,
    this.iconUrl,
    required this.isSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: isSelected
            ? AppColors.primary.withOpacity(0.2)
            : Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: isSelected
            ? Border.all(color: AppColors.primary, width: 2)
            : null,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (iconUrl != null) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: Image.network(
                iconUrl!,
                width: 24,
                height: 16,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => const Icon(
                  Icons.flag,
                  size: 16,
                  color: Colors.white70,
                ),
              ),
            ),
            const SizedBox(width: 8),
          ],
          Text(
            name,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(color: Colors.white),
          ),
        ],
      ),
    );
  }
}
