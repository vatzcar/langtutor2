# Plan 5: Flutter Profile & Support Screens

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Profile section (profile data, CEFR levels, history, subscription) and Support section with all screens matching the mockup designs.

**Architecture:** Profile screens share a common top bar with plan name and icon tabs. Each sub-screen fetches its data via Riverpod providers. Support screen uses the same call/chat components from the learning module.

**Tech Stack:** Flutter, Riverpod, Dio, GoRouter

---

### Task 1: Profile Screen with Tab Navigation

**Files:**
- Modify: `mobile/lib/screens/profile/profile_screen.dart`

- [ ] **Step 1: Implement profile screen**

```dart
// mobile/lib/screens/profile/profile_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/persona_avatar.dart';
import '../../providers/auth_provider.dart';
import '../../providers/user_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final user = authState.user;
    final planAsync = ref.watch(currentPlanProvider);

    return Column(
      children: [
        // Top bar: plan name + profile menu icons
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              // Plan name
              Text(
                planAsync.whenOrNull(data: (p) => p?.name) ?? 'Free',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              // Menu icons
              _ProfileMenuIcon(icon: Icons.person, isActive: true, onTap: () {}),
              _ProfileMenuIcon(icon: Icons.bar_chart, onTap: () => context.push('/profile/cefr')),
              _ProfileMenuIcon(icon: Icons.history, onTap: () => context.push('/profile/history')),
              _ProfileMenuIcon(icon: Icons.card_membership, onTap: () => context.push('/profile/subscription')),
            ],
          ),
        ),

        const Spacer(),

        // Profile image
        PersonaAvatar(
          imageUrl: null, // Will be loaded from user avatar
          size: 200,
          showBorder: true,
        ),

        const SizedBox(height: 24),

        // User data card
        Container(
          margin: const EdgeInsets.symmetric(horizontal: 24),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.8),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            children: [
              _InfoRow(label: 'Name', value: user?.name ?? 'N/A'),
              const Divider(height: 24),
              _InfoRow(label: 'Email', value: user?.email ?? 'N/A'),
              const Divider(height: 24),
              _InfoRow(label: 'Date of Birth', value: user?.dateOfBirth ?? 'Not set'),
              const Divider(height: 24),
              _InfoRow(label: 'Country', value: 'Auto-detected'),
            ],
          ),
        ),

        const SizedBox(height: 16),

        // Edit button
        Align(
          alignment: Alignment.centerRight,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: ElevatedButton(
              onPressed: () => context.push('/profile/edit'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.navBg,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
              child: const Text('Edit'),
            ),
          ),
        ),

        const Spacer(flex: 2),
      ],
    );
  }
}

class _ProfileMenuIcon extends StatelessWidget {
  final IconData icon;
  final bool isActive;
  final VoidCallback onTap;

  const _ProfileMenuIcon({required this.icon, this.isActive = false, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(left: 8),
        width: 42, height: 42,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isActive ? AppColors.navBg : AppColors.navBg.withOpacity(0.7),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodyMedium),
        Text(value, style: Theme.of(context).textTheme.bodyLarge),
      ],
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/profile/profile_screen.dart
git commit -m "feat: implement profile screen with user data and menu icons"
```

---

### Task 2: Profile Edit Screen

**Files:**
- Modify: `mobile/lib/screens/profile/profile_edit_screen.dart`

- [ ] **Step 1: Implement profile edit screen**

```dart
// mobile/lib/screens/profile/profile_edit_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';
import '../../providers/auth_provider.dart';

class ProfileEditScreen extends ConsumerStatefulWidget {
  const ProfileEditScreen({super.key});

  @override
  ConsumerState<ProfileEditScreen> createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends ConsumerState<ProfileEditScreen> {
  late TextEditingController _nameController;
  DateTime? _dateOfBirth;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    final user = ref.read(authProvider).user;
    _nameController = TextEditingController(text: user?.name ?? '');
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgProfile,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back),
                      onPressed: () => context.pop(),
                    ),
                    Text('Edit Profile', style: Theme.of(context).textTheme.headlineSmall),
                  ],
                ),
                const SizedBox(height: 32),

                Text('Name', style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: 8),
                TextField(controller: _nameController, decoration: const InputDecoration(hintText: 'Your name')),

                const SizedBox(height: 24),

                Text('Date of Birth', style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: 8),
                GestureDetector(
                  onTap: () async {
                    final date = await showDatePicker(
                      context: context,
                      initialDate: DateTime(2000),
                      firstDate: DateTime(1920),
                      lastDate: DateTime.now(),
                    );
                    if (date != null) setState(() => _dateOfBirth = date);
                  },
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.divider),
                    ),
                    child: Text(
                      _dateOfBirth != null
                          ? '${_dateOfBirth!.day}/${_dateOfBirth!.month}/${_dateOfBirth!.year}'
                          : 'Select date',
                      style: TextStyle(color: _dateOfBirth != null ? AppColors.textPrimary : AppColors.textMuted),
                    ),
                  ),
                ),

                const SizedBox(height: 24),

                Text('Native Language', style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: 8),
                // TODO: Language dropdown
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.divider),
                  ),
                  child: Text('Select language', style: TextStyle(color: AppColors.textMuted)),
                ),

                const Spacer(),

                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _isSaving ? null : () async {
                      setState(() => _isSaving = true);
                      try {
                        final api = ref.read(apiClientProvider);
                        await api.patch('/mobile/users/me', data: {
                          'name': _nameController.text,
                          if (_dateOfBirth != null) 'date_of_birth': _dateOfBirth!.toIso8601String().split('T')[0],
                        });
                        ref.read(authProvider.notifier).refreshUser();
                        if (mounted) context.pop();
                      } finally {
                        if (mounted) setState(() => _isSaving = false);
                      }
                    },
                    child: _isSaving ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : const Text('Save'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/profile/profile_edit_screen.dart
git commit -m "feat: implement profile edit screen"
```

---

### Task 3: CEFR Level Screen

**Files:**
- Modify: `mobile/lib/screens/profile/cefr_screen.dart`
- Create: `mobile/lib/widgets/cefr_level_tile.dart`

- [ ] **Step 1: Create CEFR level tile widget**

```dart
// mobile/lib/widgets/cefr_level_tile.dart
import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../models/cefr_level.dart';

class CefrLevelTile extends StatelessWidget {
  final CefrLevelInfo info;
  final bool isSelected;
  final VoidCallback onTap;

  const CefrLevelTile({
    super.key,
    required this.info,
    this.isSelected = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.primary.withOpacity(0.1) : AppColors.navBg.withOpacity(0.08),
          borderRadius: BorderRadius.circular(12),
          border: isSelected ? Border.all(color: AppColors.primary, width: 1.5) : null,
        ),
        child: Row(
          children: [
            Text(info.level,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: info.status == 'passed' ? AppColors.success.withOpacity(0.2) : AppColors.accent.withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                info.status == 'passed' ? 'PASSED' : 'IN PROGRESS...',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: info.status == 'passed' ? AppColors.success : AppColors.accent,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Implement CEFR screen**

```dart
// mobile/lib/screens/profile/cefr_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/cefr_level_tile.dart';
import '../../models/cefr_level.dart';
import '../../providers/language_provider.dart';
import '../../providers/user_provider.dart';
import '../../providers/auth_provider.dart';

final cefrHistoryProvider = FutureProvider<List<CefrLevelInfo>>((ref) async {
  final api = ref.read(apiClientProvider);
  final selectedLang = ref.read(selectedLanguageProvider);
  if (selectedLang == null) return [];
  final resp = await api.get('/mobile/users/me/languages/${selectedLang.id}/cefr-history');
  return (resp.data as List).map((e) => CefrLevelInfo.fromJson(e)).toList();
});

class CefrScreen extends ConsumerStatefulWidget {
  const CefrScreen({super.key});

  @override
  ConsumerState<CefrScreen> createState() => _CefrScreenState();
}

class _CefrScreenState extends ConsumerState<CefrScreen> {
  int _selectedIndex = -1; // -1 means current level selected by default

  @override
  Widget build(BuildContext context) {
    final planAsync = ref.watch(currentPlanProvider);
    final cefrAsync = ref.watch(cefrHistoryProvider);
    final selectedLang = ref.watch(selectedLanguageProvider);

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgProfile,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                // Top bar
                Row(
                  children: [
                    Text(planAsync.whenOrNull(data: (p) => p?.name) ?? '',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700)),
                    const Spacer(),
                    _menuIcon(Icons.person, false, () => context.go('/profile')),
                    _menuIcon(Icons.bar_chart, true, () {}),
                    _menuIcon(Icons.history, false, () => context.push('/profile/history')),
                    _menuIcon(Icons.card_membership, false, () => context.push('/profile/subscription')),
                  ],
                ),

                const SizedBox(height: 24),

                // Title
                Text('CEFR LEVEL', style: Theme.of(context).textTheme.headlineLarge?.copyWith(letterSpacing: 2)),

                const SizedBox(height: 16),

                // Language flag + name
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(color: AppColors.navBg, borderRadius: BorderRadius.circular(6)),
                      child: const Text('FLAG', style: TextStyle(color: Colors.white, fontSize: 10)),
                    ),
                    const SizedBox(width: 8),
                    Text('Language', style: Theme.of(context).textTheme.bodyLarge),
                  ],
                ),

                const SizedBox(height: 20),

                // CEFR levels list
                cefrAsync.when(
                  data: (levels) {
                    // Sort: passed on top, then in progress
                    final sorted = [...levels]..sort((a, b) {
                      if (a.status == 'passed' && b.status != 'passed') return -1;
                      if (a.status != 'passed' && b.status == 'passed') return 1;
                      return 0;
                    });

                    final selectedLevel = _selectedIndex >= 0 && _selectedIndex < sorted.length
                        ? sorted[_selectedIndex]
                        : sorted.isNotEmpty ? sorted.last : null;

                    return Expanded(
                      child: Column(
                        children: [
                          // Level list
                          SizedBox(
                            height: sorted.length * 56.0,
                            child: ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: sorted.length,
                              itemBuilder: (_, i) => CefrLevelTile(
                                info: sorted[i],
                                isSelected: (_selectedIndex < 0 && i == sorted.length - 1) || _selectedIndex == i,
                                onTap: () => setState(() => _selectedIndex = i),
                              ),
                            ),
                          ),

                          const SizedBox(height: 20),

                          // Analytics for selected level
                          if (selectedLevel != null)
                            Expanded(
                              child: Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.8),
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: SingleChildScrollView(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('${selectedLevel.level} Analytics',
                                          style: Theme.of(context).textTheme.headlineSmall),
                                      const SizedBox(height: 16),
                                      _AnalyticRow(label: 'Lessons', value: '${selectedLevel.lessonsCount}'),
                                      _AnalyticRow(label: 'Hours Spent', value: '${selectedLevel.hoursSpent.toStringAsFixed(1)}h'),
                                      _AnalyticRow(label: 'Streak', value: '${selectedLevel.streakDays} days'),
                                      _AnalyticRow(label: 'Progress', value: '${selectedLevel.progressPercent.toStringAsFixed(0)}%'),
                                      _AnalyticRow(label: 'Practice Sessions', value: '${selectedLevel.practiceSessions}'),
                                      _AnalyticRow(label: 'Practice Hours', value: '${selectedLevel.practiceHours.toStringAsFixed(1)}h'),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                    );
                  },
                  loading: () => const Expanded(child: Center(child: CircularProgressIndicator())),
                  error: (e, _) => Expanded(child: Center(child: Text('Error: $e'))),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _menuIcon(IconData icon, bool isActive, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(left: 8),
        width: 42, height: 42,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isActive ? AppColors.navBg : AppColors.navBg.withOpacity(0.7),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }
}

class _AnalyticRow extends StatelessWidget {
  final String label;
  final String value;

  const _AnalyticRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          Text(value, style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add mobile/lib/
git commit -m "feat: implement CEFR level screen with analytics"
```

---

### Task 4: History Screen

**Files:**
- Modify: `mobile/lib/screens/profile/history_screen.dart`

- [ ] **Step 1: Implement history screen**

```dart
// mobile/lib/screens/profile/history_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';
import '../../models/session.dart';
import '../../providers/auth_provider.dart';
import '../../providers/language_provider.dart';
import '../../providers/user_provider.dart';

final sessionHistoryProvider = FutureProvider<List<LearningSession>>((ref) async {
  final api = ref.read(apiClientProvider);
  final selectedLang = ref.read(selectedLanguageProvider);
  final params = <String, dynamic>{};
  if (selectedLang != null) params['language_id'] = selectedLang.languageId;
  final resp = await api.get('/mobile/sessions', queryParameters: params);
  return (resp.data as List).map((e) => LearningSession.fromJson(e)).toList();
});

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planAsync = ref.watch(currentPlanProvider);
    final sessionsAsync = ref.watch(sessionHistoryProvider);

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgProfile,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                // Top bar
                Row(
                  children: [
                    Text(planAsync.whenOrNull(data: (p) => p?.name) ?? '',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700)),
                    const Spacer(),
                    _menuIcon(context, Icons.person, () => context.go('/profile')),
                    _menuIcon(context, Icons.bar_chart, () => context.push('/profile/cefr')),
                    _menuIconActive(context, Icons.history),
                    _menuIcon(context, Icons.card_membership, () => context.push('/profile/subscription')),
                  ],
                ),

                const SizedBox(height: 24),

                Text('HISTORY', style: Theme.of(context).textTheme.headlineLarge?.copyWith(letterSpacing: 2)),

                const SizedBox(height: 20),

                // Session list
                Expanded(
                  child: sessionsAsync.when(
                    data: (sessions) {
                      if (sessions.isEmpty) {
                        return const Center(child: Text('No sessions yet'));
                      }

                      // Group by day number
                      int dayNum = 0;
                      String? lastDate;

                      return ListView.builder(
                        itemCount: sessions.length,
                        itemBuilder: (_, index) {
                          final session = sessions[index];
                          final date = session.startedAt.split('T')[0];
                          if (date != lastDate) {
                            dayNum++;
                            lastDate = date;
                          }

                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                SizedBox(
                                  width: 70,
                                  child: Text('Day $dayNum',
                                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700)),
                                ),
                                Expanded(
                                  child: Text(date, style: Theme.of(context).textTheme.bodyMedium),
                                ),
                                GestureDetector(
                                  onTap: () => context.push('/profile/transcript/${session.id}'),
                                  child: Text('View Session',
                                      style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w600, fontSize: 13)),
                                ),
                              ],
                            ),
                          );
                        },
                      );
                    },
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (e, _) => Center(child: Text('Error: $e')),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _menuIcon(BuildContext context, IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(left: 8), width: 42, height: 42,
        decoration: BoxDecoration(shape: BoxShape.circle, color: AppColors.navBg.withOpacity(0.7)),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }

  Widget _menuIconActive(BuildContext context, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(left: 8), width: 42, height: 42,
      decoration: const BoxDecoration(shape: BoxShape.circle, color: AppColors.navBg),
      child: Icon(icon, color: Colors.white, size: 20),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/profile/history_screen.dart
git commit -m "feat: implement history screen with session list"
```

---

### Task 5: Transcript Screen

**Files:**
- Modify: `mobile/lib/screens/profile/transcript_screen.dart`

- [ ] **Step 1: Implement transcript viewer (chat-like layout)**

```dart
// mobile/lib/screens/profile/transcript_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/chat_bubble.dart';
import '../../providers/auth_provider.dart';

final transcriptProvider = FutureProvider.family<List<Map<String, dynamic>>, String>((ref, sessionId) async {
  final api = ref.read(apiClientProvider);
  final resp = await api.get('/mobile/sessions/$sessionId/transcript');
  return List<Map<String, dynamic>>.from(resp.data);
});

class TranscriptScreen extends ConsumerWidget {
  final String sessionId;
  const TranscriptScreen({super.key, required this.sessionId});

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
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                color: AppColors.navBg,
                child: Row(
                  children: [
                    const CircleAvatar(
                      radius: 18, backgroundColor: AppColors.disabledBg,
                      child: Icon(Icons.person, color: AppColors.disabled, size: 20),
                    ),
                    const SizedBox(width: 12),
                    const Expanded(child: Text('Session Transcript', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600))),
                    IconButton(
                      icon: const Icon(Icons.arrow_back, color: Colors.white),
                      onPressed: () => context.pop(),
                    ),
                  ],
                ),
              ),

              // Messages
              Expanded(
                child: transcriptAsync.when(
                  data: (entries) => ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    itemCount: entries.length,
                    itemBuilder: (_, index) {
                      final entry = entries[index];
                      return ChatBubble(
                        message: entry['content'] ?? '',
                        isUser: entry['speaker'] == 'user',
                      );
                    },
                  ),
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (e, _) => Center(child: Text('Error: $e')),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/profile/transcript_screen.dart
git commit -m "feat: implement transcript viewer screen"
```

---

### Task 6: Subscription Screen

**Files:**
- Modify: `mobile/lib/screens/profile/subscription_screen.dart`

- [ ] **Step 1: Implement subscription screen**

```dart
// mobile/lib/screens/profile/subscription_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/bubble_background.dart';
import '../../widgets/plan_card.dart';
import '../../providers/user_provider.dart';
import '../../providers/auth_provider.dart';

class SubscriptionScreen extends ConsumerStatefulWidget {
  const SubscriptionScreen({super.key});

  @override
  ConsumerState<SubscriptionScreen> createState() => _SubscriptionScreenState();
}

class _SubscriptionScreenState extends ConsumerState<SubscriptionScreen> {
  bool _isYearly = true;

  @override
  Widget build(BuildContext context) {
    final planAsync = ref.watch(currentPlanProvider);
    final plansAsync = ref.watch(plansProvider);
    final subAsync = ref.watch(currentSubscriptionProvider);

    return Scaffold(
      body: BubbleBackground(
        backgroundColor: AppColors.bgProfile,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                // Top bar
                Row(
                  children: [
                    Text(planAsync.whenOrNull(data: (p) => p?.name) ?? '',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700)),
                    const Spacer(),
                    _menuIcon(context, Icons.person, () => context.go('/profile')),
                    _menuIcon(context, Icons.bar_chart, () => context.push('/profile/cefr')),
                    _menuIcon(context, Icons.history, () => context.push('/profile/history')),
                    _menuIconActive(context, Icons.card_membership),
                  ],
                ),

                const SizedBox(height: 16),

                // Monthly / Yearly toggle
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('Monthly', style: TextStyle(
                      fontWeight: !_isYearly ? FontWeight.w700 : FontWeight.w400,
                      color: !_isYearly ? AppColors.textPrimary : AppColors.textMuted,
                    )),
                    const SizedBox(width: 12),
                    Switch(value: _isYearly, onChanged: (v) => setState(() => _isYearly = v), activeColor: AppColors.primary),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Yearly', style: TextStyle(
                          fontWeight: _isYearly ? FontWeight.w700 : FontWeight.w400,
                          color: _isYearly ? AppColors.textPrimary : AppColors.textMuted,
                        )),
                        if (_isYearly)
                          plansAsync.whenOrNull(data: (plans) {
                            final ultra = plans.where((p) => p.slug == 'ultra').firstOrNull;
                            if (ultra != null && ultra.yearlySavings > 0) {
                              return Text('Save ${ultra.yearlySavings.toStringAsFixed(0)}%',
                                  style: TextStyle(fontSize: 11, color: AppColors.success, fontWeight: FontWeight.w600));
                            }
                            return null;
                          }) ?? const SizedBox(),
                      ],
                    ),
                  ],
                ),

                const SizedBox(height: 16),

                // Plan cards
                Expanded(
                  child: plansAsync.when(
                    data: (plans) {
                      final currentPlan = planAsync.whenOrNull(data: (p) => p);
                      final currentSub = subAsync.whenOrNull(data: (s) => s);

                      return ListView(
                        children: plans.map((plan) => PlanCard(
                          plan: plan,
                          isYearly: _isYearly,
                          isSelected: currentPlan?.id == plan.id,
                          onSelect: () async {
                            final api = ref.read(apiClientProvider);
                            await api.post('/mobile/subscriptions/change', data: {
                              'plan_id': plan.id,
                              'billing_cycle': _isYearly ? 'yearly' : 'monthly',
                            });
                            ref.invalidate(currentSubscriptionProvider);
                            ref.invalidate(currentPlanProvider);
                          },
                        )).toList(),
                      );
                    },
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (e, _) => Center(child: Text('Error: $e')),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _menuIcon(BuildContext context, IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(left: 8), width: 42, height: 42,
        decoration: BoxDecoration(shape: BoxShape.circle, color: AppColors.navBg.withOpacity(0.7)),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }

  Widget _menuIconActive(BuildContext context, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(left: 8), width: 42, height: 42,
      decoration: const BoxDecoration(shape: BoxShape.circle, color: AppColors.navBg),
      child: Icon(icon, color: Colors.white, size: 20),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/profile/subscription_screen.dart
git commit -m "feat: implement subscription screen with plan cards and billing toggle"
```

---

### Task 7: Support Screen

**Files:**
- Modify: `mobile/lib/screens/support/support_screen.dart`

- [ ] **Step 1: Implement support screen**

```dart
// mobile/lib/screens/support/support_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';
import '../../widgets/top_info_bar.dart';
import '../../models/session.dart';
import '../../providers/auth_provider.dart';
import '../../providers/language_provider.dart';
import '../../providers/user_provider.dart';
import '../../providers/session_provider.dart';

final supportHistoryProvider = FutureProvider<List<LearningSession>>((ref) async {
  final api = ref.read(apiClientProvider);
  final resp = await api.get('/mobile/support/history');
  return (resp.data as List).map((e) => LearningSession.fromJson(e)).toList();
});

class SupportScreen extends ConsumerStatefulWidget {
  const SupportScreen({super.key});

  @override
  ConsumerState<SupportScreen> createState() => _SupportScreenState();
}

class _SupportScreenState extends ConsumerState<SupportScreen> {
  bool _showOptions = false;

  @override
  Widget build(BuildContext context) {
    final selectedLang = ref.watch(selectedLanguageProvider);
    final planAsync = ref.watch(currentPlanProvider);
    final historyAsync = ref.watch(supportHistoryProvider);

    return Stack(
      children: [
        Column(
          children: [
            // Top Info Bar (same as home)
            TopInfoBar(
              cefrLevel: selectedLang?.currentCefrLevel ?? 'A0',
              progressPercent: selectedLang?.cefrProgressPercent ?? 0,
              planName: planAsync.whenOrNull(data: (plan) => plan?.name) ?? 'Free',
            ),

            const SizedBox(height: 8),

            // Support history list
            Expanded(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.6),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('SUPPORT HISTORY',
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(letterSpacing: 1)),
                    const SizedBox(height: 16),

                    Expanded(
                      child: historyAsync.when(
                        data: (sessions) {
                          if (sessions.isEmpty) {
                            return const Center(child: Text('No support history yet'));
                          }
                          return ListView.separated(
                            itemCount: sessions.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 8),
                            itemBuilder: (_, index) {
                              final session = sessions[index];
                              return Container(
                                padding: const EdgeInsets.all(14),
                                decoration: BoxDecoration(
                                  border: Border.all(color: AppColors.divider),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text('Support Session',
                                              style: Theme.of(context).textTheme.bodyLarge),
                                          Text(session.startedAt.split('T')[0],
                                              style: Theme.of(context).textTheme.bodySmall),
                                        ],
                                      ),
                                    ),
                                    GestureDetector(
                                      onTap: () => context.push('/profile/transcript/${session.id}'),
                                      child: Icon(Icons.chevron_right, color: AppColors.textMuted),
                                    ),
                                  ],
                                ),
                              );
                            },
                          );
                        },
                        loading: () => const Center(child: CircularProgressIndicator()),
                        error: (e, _) => Center(child: Text('Error: $e')),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),

        // FAB + options
        Positioned(
          bottom: 16,
          right: 16,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Options menu (slides in)
              if (_showOptions)
                Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: AppColors.navBg,
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 8)],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _SupportOption(
                        label: 'VIDEO CALL',
                        enabled: planAsync.whenOrNull(data: (p) => p?.hasVideoCall) ?? false,
                        onTap: () => _startSupport(context, ref, 'video_call'),
                      ),
                      const SizedBox(height: 8),
                      _SupportOption(
                        label: 'VOICE CALL',
                        enabled: planAsync.whenOrNull(data: (p) => p?.hasVoiceCall) ?? false,
                        onTap: () => _startSupport(context, ref, 'voice_call'),
                      ),
                      const SizedBox(height: 8),
                      _SupportOption(
                        label: 'CHAT',
                        enabled: true,
                        onTap: () => _startSupport(context, ref, 'text_chat'),
                      ),
                    ],
                  ),
                ),

              // FAB
              GestureDetector(
                onTap: () => setState(() => _showOptions = !_showOptions),
                child: Container(
                  width: 56, height: 56,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.navBg,
                    boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 6)],
                  ),
                  child: const Icon(Icons.message, color: Colors.white),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _startSupport(BuildContext context, WidgetRef ref, String type) async {
    setState(() => _showOptions = false);
    await ref.read(sessionProvider.notifier).startSession(type, 'support');
    if (!context.mounted) return;
    switch (type) {
      case 'video_call':
        context.push('/learning/video', extra: 'support');
      case 'voice_call':
        context.push('/learning/voice', extra: 'support');
      case 'text_chat':
        context.push('/learning/chat', extra: 'support');
    }
  }
}

class _SupportOption extends StatelessWidget {
  final String label;
  final bool enabled;
  final VoidCallback onTap;

  const _SupportOption({required this.label, required this.enabled, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: Text(
        label,
        style: TextStyle(
          color: enabled ? Colors.white : AppColors.disabled,
          fontWeight: FontWeight.w600,
          fontSize: 14,
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/screens/support/
git commit -m "feat: implement support screen with history and FAB options menu"
```
