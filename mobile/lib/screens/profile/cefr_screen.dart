import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../models/cefr_level.dart';
import '../../providers/auth_provider.dart';
import '../../providers/language_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../widgets/bubble_background.dart';

// ---------------------------------------------------------------------------
// Provider: CEFR history for the selected language
// ---------------------------------------------------------------------------

final cefrHistoryProvider =
    FutureProvider.family<List<CefrLevelInfo>, String>((ref, langId) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient
      .get('/mobile/users/me/languages/$langId/cefr-history');
  final items = response.data as List<dynamic>;
  return items
      .map((e) => CefrLevelInfo.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ---------------------------------------------------------------------------
// CefrScreen
// ---------------------------------------------------------------------------

class CefrScreen extends ConsumerStatefulWidget {
  const CefrScreen({super.key});

  @override
  ConsumerState<CefrScreen> createState() => _CefrScreenState();
}

class _CefrScreenState extends ConsumerState<CefrScreen> {
  String? _selectedLevel;

  void _navigateTab(BuildContext context, int index) {
    const routes = ['/home', '/practice', '/profile', '/support'];
    if (index < routes.length) context.go(routes[index]);
  }

  @override
  Widget build(BuildContext context) {
    final plan = ref.watch(currentPlanProvider);
    final planName = plan.whenOrNull(data: (p) => p?.name) ?? '';
    final selectedLang = ref.watch(selectedLanguageProvider);
    final langId = selectedLang?['id'] as String?;
    final langName = selectedLang?['name'] as String? ?? 'Language';
    final flagUrl = selectedLang?['icon_url'] as String?;

    final historyAsync =
        langId != null ? ref.watch(cefrHistoryProvider(langId)) : null;

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgProfile,
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 12),

              // Top row (same as profile)
              _buildTopRow(context, planName),

              const SizedBox(height: 20),

              // Title
              Text(
                'CEFR LEVEL',
                style: Theme.of(context)
                    .textTheme
                    .headlineMedium
                    ?.copyWith(letterSpacing: 3),
              ),

              const SizedBox(height: 8),

              // Language flag + name
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (flagUrl != null)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: Image.network(flagUrl,
                          width: 24,
                          height: 16,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) =>
                              const SizedBox.shrink()),
                    ),
                  const SizedBox(width: 8),
                  Text(
                    langName,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 16),

              // CEFR level list + analytics
              Expanded(
                child: historyAsync == null
                    ? const Center(child: Text('No language selected'))
                    : historyAsync.when(
                        loading: () => const Center(
                            child: CircularProgressIndicator()),
                        error: (e, _) =>
                            Center(child: Text('Error: $e')),
                        data: (levels) =>
                            _buildContent(levels),
                      ),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: 2,
        onTap: (i) => _navigateTab(context, i),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Sub-builds
  // ---------------------------------------------------------------------------

  Widget _buildTopRow(BuildContext context, String planName) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Text(
            planName,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const Spacer(),
          _MenuIcon(
            icon: Icons.person_rounded,
            isActive: false,
            onTap: () => context.go('/profile'),
          ),
          const SizedBox(width: 10),
          _MenuIcon(
            icon: Icons.bar_chart_rounded,
            isActive: true,
            onTap: () {},
          ),
          const SizedBox(width: 10),
          _MenuIcon(
            icon: Icons.history_rounded,
            isActive: false,
            onTap: () => context.push('/profile/history'),
          ),
          const SizedBox(width: 10),
          _MenuIcon(
            icon: Icons.credit_card_rounded,
            isActive: false,
            onTap: () => context.push('/profile/subscription'),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(List<CefrLevelInfo> levels) {
    // Sort: passed on top.
    final sorted = List<CefrLevelInfo>.from(levels)
      ..sort((a, b) {
        if (a.status == 'passed' && b.status != 'passed') return -1;
        if (a.status != 'passed' && b.status == 'passed') return 1;
        return 0;
      });

    final selected = _selectedLevel != null
        ? sorted.cast<CefrLevelInfo?>().firstWhere(
              (l) => l!.level == _selectedLevel,
              orElse: () => null,
            )
        : null;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          // Level tiles
          ...sorted.map((l) => _CefrLevelTile(
                info: l,
                isSelected: l.level == _selectedLevel,
                onTap: () => setState(() => _selectedLevel = l.level),
              )),

          // Analytics panel
          if (selected != null) ...[
            const SizedBox(height: 20),
            _AnalyticsPanel(info: selected),
          ],
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// CEFR level tile
// ---------------------------------------------------------------------------

class _CefrLevelTile extends StatelessWidget {
  const _CefrLevelTile({
    required this.info,
    required this.isSelected,
    required this.onTap,
  });

  final CefrLevelInfo info;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isPassed = info.status == 'passed';

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primary.withValues(alpha: 0.12)
              : Colors.white.withValues(alpha: 0.8),
          borderRadius: BorderRadius.circular(12),
          border: isSelected
              ? Border.all(color: AppColors.primary, width: 2)
              : null,
        ),
        child: Row(
          children: [
            Text(
              info.level,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: isPassed ? AppColors.success : AppColors.textPrimary,
              ),
            ),
            const Spacer(),
            if (isPassed)
              const Icon(Icons.check_circle_rounded,
                  color: AppColors.success, size: 22),
            if (!isPassed)
              Text(
                '${info.progressPercent.toInt()}%',
                style: const TextStyle(
                  fontSize: 14,
                  color: AppColors.textMuted,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Analytics panel
// ---------------------------------------------------------------------------

class _AnalyticsPanel extends StatelessWidget {
  const _AnalyticsPanel({required this.info});

  final CefrLevelInfo info;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${info.level} Analytics',
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 16),
          _StatRow('Lessons', '${info.lessonsCount}'),
          _StatRow('Hours', info.hoursSpent.toStringAsFixed(1)),
          _StatRow('Streak', '${info.streakDays} days'),
          _StatRow('Progress', '${info.progressPercent.toInt()}%'),
          _StatRow('Practice Sessions', '${info.practiceSessions}'),
          _StatRow('Practice Hours', info.practiceHours.toStringAsFixed(1)),
        ],
      ),
    );
  }
}

class _StatRow extends StatelessWidget {
  const _StatRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 14, color: AppColors.textSecondary)),
          Text(value,
              style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Shared menu icon (duplicated from profile_screen for independence)
// ---------------------------------------------------------------------------

class _MenuIcon extends StatelessWidget {
  const _MenuIcon({
    required this.icon,
    required this.isActive,
    required this.onTap,
  });

  final IconData icon;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: AppColors.navBg,
          shape: BoxShape.circle,
          border: isActive
              ? Border.all(color: AppColors.navActive, width: 2)
              : null,
        ),
        child: Icon(
          icon,
          color: isActive ? AppColors.navActive : Colors.white70,
          size: 20,
        ),
      ),
    );
  }
}
