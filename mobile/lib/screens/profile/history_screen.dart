import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../models/session.dart';
import '../../providers/auth_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../widgets/bubble_background.dart';

// ---------------------------------------------------------------------------
// Provider: session history
// ---------------------------------------------------------------------------

final sessionHistoryProvider =
    FutureProvider<List<LearningSession>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get('/mobile/sessions');
  final items = response.data as List<dynamic>;
  return items
      .map((e) => LearningSession.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ---------------------------------------------------------------------------
// HistoryScreen
// ---------------------------------------------------------------------------

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final plan = ref.watch(currentPlanProvider);
    final planName = plan.whenOrNull(data: (p) => p?.name) ?? '';
    final historyAsync = ref.watch(sessionHistoryProvider);

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgProfile,
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 12),

              // Top row
              _buildTopRow(context, planName),

              const SizedBox(height: 20),

              Text(
                'HISTORY',
                style: Theme.of(context)
                    .textTheme
                    .headlineMedium
                    ?.copyWith(letterSpacing: 3),
              ),

              const SizedBox(height: 16),

              // Session list
              Expanded(
                child: historyAsync.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (e, _) => Center(child: Text('Error: $e')),
                  data: (sessions) => sessions.isEmpty
                      ? const Center(child: Text('No sessions yet'))
                      : ListView.builder(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          itemCount: sessions.length,
                          itemBuilder: (_, index) {
                            final session = sessions[index];
                            return _SessionCard(
                              dayNumber: index + 1,
                              session: session,
                            );
                          },
                        ),
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
            isActive: false,
            onTap: () => context.push('/profile/cefr'),
          ),
          const SizedBox(width: 10),
          _MenuIcon(
            icon: Icons.history_rounded,
            isActive: true,
            onTap: () {},
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

  void _navigateTab(BuildContext context, int index) {
    const routes = ['/home', '/practice', '/profile', '/support'];
    if (index < routes.length) context.go(routes[index]);
  }
}

// ---------------------------------------------------------------------------
// Session card
// ---------------------------------------------------------------------------

class _SessionCard extends StatelessWidget {
  const _SessionCard({required this.dayNumber, required this.session});

  final int dayNumber;
  final LearningSession session;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Day $dayNumber',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                session.startedAt.split('T').first,
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
          const Spacer(),
          GestureDetector(
            onTap: () =>
                context.push('/profile/transcript/${session.id}'),
            child: const Text(
              'View Session',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppColors.primary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Menu icon
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
