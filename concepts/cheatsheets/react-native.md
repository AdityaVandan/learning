# React Native Cheatsheet

Interview revision guide covering the 80/20 concepts every React Native engineer should know, plus an exhaustive version-by-version feature history from inception through current releases.

**Last updated:** June 2026 (covers through **0.85.x** stable; **0.86** in RC).

**Official references:** [reactnative.dev](https://reactnative.dev) · [Upgrade Helper](https://react-native-upgrade-helper.github.io/) · [GitHub Releases](https://github.com/facebook/react-native/releases) · [React Native Archive](https://archive.reactnative.dev/) (docs for versions &lt; 0.60)

---

## Part 1: 80/20 — Interview Essentials

### 1.1 What React Native Is (and Is Not)

| Concept | Detail |
|--------|--------|
| **Definition** | Framework to build native mobile UIs using React; JS drives a tree of native views (UIKit / Android Views), not a WebView for the main UI |
| **Not** | A web app in a browser; not “write once, run anywhere” without platform tweaks |
| **JS thread** | Runs React reconciliation, business logic, and calls into native via bridge/JSI |
| **UI thread** | Native layout and rendering; must stay unblocked for 60fps |
| **Bundlers** | **Metro** (default): transforms, bundles, serves HMR/Fast Refresh |
| **Engines** | **Hermes** (default since 0.70; **Hermes V1** default since 0.84); **JSC** moved to community package (0.79+) |

### 1.2 Architecture: Legacy vs New (Critical for Interviews)

```text
LEGACY (frozen ~2025, removed as runtime option in 0.82+)
  JS ──async JSON──► Bridge ──► Native Modules / UIManager

NEW ARCHITECTURE (default 0.76+, mandatory 0.82+)
  JS ◄──JSI (sync C++ refs)──► TurboModules (native modules)
  JS ◄──Fabric (C++ renderer)──► Native views
  Codegen: generates type-safe C++/Java/ObjC++ from Flow/TS specs
```

| Piece | Role |
|-------|------|
| **JSI** | JavaScript Interface; hold C++ object refs; invoke methods without async serialization |
| **Fabric** | New renderer; shadow tree on C++; supports React 18 concurrent features, synchronous layout in many paths |
| **TurboModules** | Lazy-loaded native modules; direct JSI calls |
| **Codegen** | `codegenConfig` in `package.json`; generates native stubs from JS specs |
| **Bridgeless** | No legacy bridge instance (0.73+ experimental, 0.74+ default with New Arch) |
| **Interop layers** | Run old native modules / Paper components under New Architecture |

**Interview sound bite:** “Bridge batched async JSON; New Architecture uses JSI + Fabric + TurboModules for sync native calls and React 18 concurrency.”

### 1.3 Core Components & APIs (High Frequency)

> **Revision:** Flexbox patterns → [§1.4](#14-flexbox--layout-yoga--react-native-refresher) · Runnable examples → [§1.13](#113-code-snippets--component--api-revision)

| API | Use | Interview note |
|-----|-----|----------------|
| `View` | Layout container | Flexbox via Yoga; no DOM |
| `Text` | All text must be wrapped | Nested `Text` for styling spans |
| `Image` | Local (`require`) / remote `uri` | Android XML drawables (0.78+) |
| `ScrollView` | Scroll all children | Heavy if many children |
| `FlatList` | Virtualized lists | `keyExtractor`, `getItemLayout`, `windowSize`, `removeClippedSubviews` |
| `SectionList` | Sectioned lists | |
| `TextInput` | Controlled/uncontrolled input | Platform keyboards, `secureTextEntry` |
| `Pressable` | Preferred touchable (0.63+) | Replaces many `Touchable*` patterns |
| `Modal` | Native modal presentation | |
| `SafeAreaView` | **Deprecated 0.81** | Use `react-native-safe-area-context` |
| `StyleSheet.create` | Register styles once | Invalid keys fail silently (0.72+) |
| `Platform` | `OS`, `select`, `Version` | Platform-specific files: `.ios.js`, `.android.js` |
| `Dimensions` / `useWindowDimensions` | Screen size | Prefer hook (0.61+) |
| `PixelRatio` | dp ↔ px | |
| `Animated` | JS-driven animations | `useNativeDriver: true` when transform/opacity only; layout props with New Animation Backend (0.85+) |
| `LayoutAnimation` | Simple layout transitions | Android `UIManager.setLayoutAnimationEnabledExperimental` |
| `Linking` | Deep links, URLs | |
| `AppState` | foreground/background | |
| `Keyboard` | `KeyboardAvoidingView`, events | |
| `StatusBar` | System status bar | |
| `RefreshControl` | Pull-to-refresh | |
| `ActivityIndicator` | Loading spinner | |

### 1.4 Flexbox & Layout (Yoga) — React Native Refresher

React Native uses **Yoga** (not browser CSS). Almost all layout is Flexbox. There is no `display: block` / `inline` / `grid` (except **`display: 'none' | 'flex' | 'contents'`** on New Architecture).

#### RN vs Web — memorize these differences

| Topic | Web (default) | React Native (default) |
|-------|---------------|-------------------------|
| Root flex direction | `row` | **`column`** |
| `flex` shorthand | Often `0 1 auto` on children | **`0`** on `<View>` (no grow/shrink) — child won't fill parent unless you set `flex: 1` or `flexGrow: 1` |
| Units | `px`, `%`, `em`, `rem`, `vh`… | **Unitless numbers = dp** (density-independent). `%` on width/height and (0.75+) gap/translate |
| `position` | `static`, `relative`, `fixed`, `sticky`… | Only **`relative`** (default) and **`absolute`** — no `fixed` / `sticky` |
| `overflow` | Well supported | **`visible`** / **`hidden`** only; no `scroll` on View (use `ScrollView`) |
| Percentage height | Common | Often **fails** unless parent has explicit height — classic “full height” bug |
| Gap | Modern browsers | **`gap` / `rowGap` / `columnGap`** (0.71+); `%` gaps (0.75+) |
| `box-sizing` | `content-box` default | **`border-box` default** on New Arch; web-like `content-box` opt-in (0.77+) |

#### Mental model: main axis & cross axis

```text
flexDirection: 'column' (DEFAULT)     flexDirection: 'row'
  main axis ↓                           main axis →
  cross axis →                          cross axis ↓

justifyContent  → along MAIN axis     alignItems      → along CROSS axis
alignItems      → along CROSS axis     justifyContent  → along MAIN axis
alignSelf       → override ONE child on cross axis
```

#### The props you actually use daily

| Prop | Values (common) | Effect |
|------|-----------------|--------|
| `flexDirection` | `'column'`, `'row'`, `'column-reverse'`, `'row-reverse'` | Main axis direction |
| `flexWrap` | `'nowrap'`, `'wrap'`, `'wrap-reverse'` | Multi-line (rare on mobile) |
| `justifyContent` | `'flex-start'`, `'center'`, `'flex-end'`, `'space-between'`, `'space-around'`, `'space-evenly'` | Main-axis distribution |
| `alignItems` | `'stretch'`, `'flex-start'`, `'center'`, `'flex-end'`, `'baseline'` | Cross-axis alignment of children |
| `alignContent` | Same family as `justifyContent` | When `flexWrap: 'wrap'`, aligns **lines** |
| `alignSelf` | Overrides `alignItems` for one child | e.g. `'flex-end'` on a single button |
| `flex` | Number shorthand: `flex: 1` ≈ grow to fill | **`flex: 1`** = “take remaining space” (interview classic) |
| `flexGrow` / `flexShrink` / `flexBasis` | Numbers / `%` / `'auto'` | Fine-grained; `flexBasis: 'auto'` + `flexGrow: 1` common |
| `gap` / `rowGap` / `columnGap` | dp or `%` (0.75+) | Space between children (no margin hacks) |
| `width` / `height` | number, `%`, `'auto'` | Parent must constrain `%` height |
| `minWidth` / `maxHeight` / … | number, `%` | Clamping |
| `aspectRatio` | number e.g. `16/9` | One dimension derives the other |
| `position` | `'relative'`, `'absolute'` | Absolute: out of flow; needs `top/left/right/bottom` |
| `top` / `left` / `right` / `bottom` | number, `%` | Anchor for absolute children |
| `zIndex` | number | iOS stacking; Android use with `elevation` for Material |
| `elevation` | Android shadow/layer | Android-only |
| `overflow` | `'visible'`, `'hidden'` | Clip children; required for some `borderRadius` clips |

#### Recipe layouts (copy-paste patterns)

**Screen root — full screen column:**

```javascript
const styles = StyleSheet.create({
  screen: { flex: 1 }, // fills window; default col direction
});
```

**Center one child (login, empty state):**

```javascript
centered: {
  flex: 1,
  justifyContent: 'center',
  alignItems: 'center',
},
```

**Header + scrollable body + footer (column):**

```javascript
container: { flex: 1 },
header: { /* fixed height or intrinsic */ },
body: { flex: 1 }, // ScrollView/FlatList with flex:1 inside
footer: { /* fixed height */ },
```

**Horizontal row — avatar + text + chevron:**

```javascript
row: {
  flexDirection: 'row',
  alignItems: 'center',
  gap: 12,
},
title: { flex: 1 }, // text takes remaining width; truncates with numberOfLines
```

**Space-between toolbar:**

```javascript
toolbar: {
  flexDirection: 'row',
  justifyContent: 'space-between',
  alignItems: 'center',
  paddingHorizontal: 16,
  height: 56,
},
```

**Absolute overlay (badge, FAB, dismiss backdrop):**

```javascript
overlay: {
  ...StyleSheet.absoluteFillObject, // or absoluteFill (0.85+)
  justifyContent: 'center',
  alignItems: 'center',
  backgroundColor: 'rgba(0,0,0,0.5)',
},
fab: {
  position: 'absolute',
  right: 16,
  bottom: 32,
},
```

**Equal-width columns (three tabs):**

```javascript
tabRow: { flexDirection: 'row' },
tab: { flex: 1, alignItems: 'center' },
```

**Aspect-ratio image box (16:9):**

```javascript
imageBox: { width: '100%', aspectRatio: 16 / 9 },
```

#### Common layout pitfalls (interview favorites)

1. **Child not visible / zero height** — Parent has no height; add `flex: 1` on parent chain or explicit `height`.
2. **`height: '100%'` fails** — Use `flex: 1` on the stretching child instead.
3. **Text overflows row** — Wrap text in `flex: 1` + `numberOfLines` + `ellipsizeMode`.
4. **`ScrollView` inside `ScrollView`** — Avoid; use one scroll container or `FlatList` with `ListHeaderComponent`.
5. **Safe area** — Don't rely on padding only; use `react-native-safe-area-context` `SafeAreaProvider` + `useSafeAreaInsets()`.
6. **Android elevation vs iOS shadow** — Different props; `boxShadow` (New Arch) aligns with web.

#### Other styling notes

- **New Arch CSS-like props:** `boxShadow`, `filter` (0.76+), `display: 'contents'`, `boxSizing`, `mixBlendMode`, `outline*` (0.77+)
- **`StyleSheet.create`** — registers styles once; invalid keys fail silently (0.72+)
- **`PixelRatio.getFontScale()`** — respect accessibility font scaling on `Text`

### 1.5 Navigation & App Structure (Ecosystem)

RN core does **not** ship a router. Know these for interviews:

| Library | Pattern |
|---------|---------|
| **React Navigation** | Stack, tab, drawer; JS navigation |
| **React Native Navigation (Wix)** | Native navigation controllers |
| **Expo Router** | File-based routing on Expo |

**Deep linking:** `Linking` + navigation `linking` config.

### 1.6 Native Modules & Native Components

| Topic | Detail |
|-------|--------|
| **Native Module** | Expose platform APIs to JS (`AsyncStorage` was core; now community) |
| **Native Component** | Custom native UI view (`requireNativeComponent` / Fabric components) |
| **Autolinking** | 0.60+: CLI discovers native deps; no manual `react-native link` |
| **TurboModule spec** | JS/TS spec + Codegen → C++/Java/ObjC++ |
| **Brownfield** | Embed RN in existing app (`ReactNativeFactory` / `RCTHost` 0.78+) |
| **Expo modules** | Config plugins, prebuild, managed workflow |

### 1.7 Performance (Must-Know Checklist)

1. **Hermes** — smaller bundle, faster startup, ahead-of-time bytecode
2. **Inline Requires** — default 0.64+; defer module eval until used
3. **`useNativeDriver: true`** — animates on native thread when possible
4. **FlatList tuning** — `getItemLayout`, `maxToRenderPerBatch`, `initialNumToRender`, memoized `renderItem`
5. **Avoid bridge chatter** — batch updates; prefer New Architecture for heavy native↔JS traffic
6. **Images** — resize, cache (e.g. `react-native-fast-image`), correct dimensions
7. **Re-renders** — `React.memo`, `useCallback`, `useMemo`; avoid anonymous functions in lists
8. **Profiling** — React Native DevTools Performance panel (0.83+), `performance.mark` / `PerformanceObserver`
9. **RAM bundles / code splitting** — Metro `inlineRequires`, optional RAM bundle for huge apps
10. **Release builds** — ProGuard/R8 Android; strip dev; enable Hermes

### 1.8 Developer Experience

| Tool | Purpose |
|------|---------|
| **Fast Refresh** | 0.61+; preserves state when possible |
| **React Native DevTools** | 0.76+ default; CDP-based; replaces Flipper for many flows |
| **Metro** | Bundler; `metro.config.js`; symlinks stable 0.73+; package `exports` default 0.79+ |
| **Upgrade Helper** | Diff templates between versions |
| **LogBox** | 0.63+ unified warnings/errors |
| **TypeScript** | Built-in types 0.71+; Strict TS API opt-in 0.80+ |
| **Flipper** | 0.62 default; declining; DevTools preferred |

### 1.9 Platform-Specific Interview Topics

**Android**

- Gradle, `minSdkVersion` / `targetSdkVersion`, AndroidX (0.60+)
- Permissions in `AndroidManifest.xml`
- Back button: `BackHandler`; predictive back (0.81+ / Android 16)
- Edge-to-edge, 16 KB page size (0.77+)
- New Architecture: `newArchEnabled` (until 0.82), Fabric, CMake builds (0.70+)
- `debugOptimized` build type (0.82+)

**iOS**

- CocoaPods, `Podfile`, `use_frameworks!`
- Xcode, signing, `Info.plist` permissions
- Safe areas, notches
- AppDelegate / `RCTAppDependencyProvider` (0.77+ template)
- Swift template default 0.77; ObjC++ still supported

### 1.10 Testing

| Layer | Tools |
|-------|-------|
| Unit | Jest + `@react-native/jest-preset` (0.85+: separate package) |
| Component | React Test Renderer, Testing Library |
| E2E | Detox, Maestro, Appium |
| Native | XCTest, Espresso |

### 1.11 Security & Storage

- **Never** ship API secrets in JS bundle
- **Keychain / Keystore** for tokens (e.g. `react-native-keychain`)
- **MMKV / Async Storage** — know encryption limits
- **SSL pinning** — native or library
- **OTA updates** — CodePush / Expo Updates (policy & store rules)

### 1.12 Common Interview Questions (Quick Answers)

| Question | Answer sketch |
|----------|----------------|
| RN vs Flutter? | RN = React + native widgets; Flutter = Skia canvas + Dart |
| Why is list scrolling janky? | Too many re-renders, heavy `renderItem`, no `getItemLayout`, images, bridge traffic |
| What is the bridge? | Legacy async queue serializing native↔JS calls; removed in Bridgeless/New Arch path |
| Hermes vs JSC? | Hermes: AOT bytecode, mobile-tuned GC; JSC community-maintained |
| How do you debug native crashes? | Xcode/Android Studio logs, symbolicated stacks, reproduce in release |
| Monorepo support? | Metro symlinks (0.72 beta, 0.73 stable), `watchFolders`, `nodeModulesPaths` |
| Upgrade strategy? | Upgrade Helper, RN version → Expo SDK matrix, enable New Arch before 0.82 |
| Fabric vs Paper? | Paper = old renderer; Fabric = new renderer in New Architecture |

### 1.13 Code Snippets — Component & API Revision

TypeScript-style examples; patterns apply to JavaScript. Import from `'react-native'` unless noted.

**Quick index:** [App & safe area](#app-entry--safe-area-start-here) · [View](#view--layout-container) · [Text](#text--all-strings-must-be-inside-text) · [Image](#image--local-asset-remote-uri-sizing) · [ScrollView](#scrollview--scroll-all-children-small-lists-only) · [FlatList](#flatlist--virtualized-list-default-for-long-data) · [SectionList](#sectionlist--grouped-sections) · [TextInput](#textinput--controlled-input-validation-focus) · [Pressable](#pressable--preferred-touch-target-replaces-touchableopacity) · [Modal](#modal--native-modal-layer) · [Switch](#switch--boolean-toggle) · [ActivityIndicator](#activityindicator--loading-spinner) · [StatusBar](#statusbar--system-bar-per-screen) · [Keyboard](#keyboard--keyboardavoidingview) · [Animated](#animated--timing-spring-native-driver) · [LayoutAnimation](#layoutanimation--easy-layout-transitions-enable-on-android) · [Linking](#linking--deep-links--external-urls) · [AppState](#appstate--foreground--background) · [Appearance](#appearance--usecolorscheme--light--dark) · [Platform](#platform--os-branching--version-checks) · [Dimensions](#dimensions--usewindowdimensions) · [PixelRatio](#pixelratio--dp-vs-physical-pixels) · [StyleSheet](#stylesheet--compose-absolute-fill-transforms) · [BackHandler](#backhandler--android-hardware-back) · [Alert](#alert--native-alert-dialog) · [Native modules](#native-modules-bridge--turbomodule-mental-model)

> **Legacy touchables:** `TouchableOpacity` / `TouchableHighlight` still work; prefer **`Pressable`** for style-as-function, better accessibility, and future APIs.

#### App entry & safe area (start here)

```tsx
// index.js — register root component
import { AppRegistry } from 'react-native';
import App from './App';
import { name as appName } from './app.json';
AppRegistry.registerComponent(appName, () => App);
```

```tsx
// App.tsx — prefer safe-area-context (SafeAreaView in core is deprecated 0.81+)
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

export default function App() {
  return (
    <SafeAreaProvider>
      <SafeAreaView style={{ flex: 1 }} edges={['top', 'left', 'right']}>
        {/* screens */}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}
```

```tsx
// Fine-grained insets (notch, home indicator, Android status bar)
import { useSafeAreaInsets } from 'react-native-safe-area-context';

function Screen() {
  const insets = useSafeAreaInsets();
  return (
    <View style={{ flex: 1, paddingTop: insets.top, paddingBottom: insets.bottom }}>
      {/* content */}
    </View>
  );
}
```

---

#### `View` — layout container

```tsx
import { View, StyleSheet } from 'react-native';

<View style={styles.card}>
  <View style={styles.row}>
    <View style={styles.badge} />
    <View style={styles.fill} />
  </View>
</View>

const styles = StyleSheet.create({
  card: {
    flex: 1,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
    overflow: 'hidden', // clip children to radius
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  badge: { width: 8, height: 8, borderRadius: 4, backgroundColor: 'red' },
  fill: { flex: 1, height: 40, backgroundColor: '#eee' },
});
```

---

#### `Text` — all strings must be inside Text

```tsx
import { Text, StyleSheet } from 'react-native';

// Basic + truncation
<Text style={styles.title} numberOfLines={2} ellipsizeMode="tail">
  Long headline that truncates after two lines
</Text>

// Nested Text = inline styles (bold link inside sentence)
<Text style={styles.body}>
  I agree to the{' '}
  <Text style={styles.link} onPress={() => openTerms()}>
    Terms of Service
  </Text>
</Text>

// Selectable, accessibility
<Text selectable accessibilityRole="header">
  Section title
</Text>

const styles = StyleSheet.create({
  title: { fontSize: 18, fontWeight: '600', color: '#111' },
  body: { fontSize: 16, lineHeight: 24, color: '#333' },
  link: { color: '#0066cc', textDecorationLine: 'underline' },
});
```

---

#### `Image` — local asset, remote URI, sizing

```tsx
import { Image, StyleSheet } from 'react-native';

// Local — require() at build time
<Image source={require('./assets/logo.png')} style={styles.icon} />

// Remote — always set dimensions (layout + cache)
<Image
  source={{ uri: 'https://example.com/photo.jpg', cache: 'force-cache' }}
  style={styles.avatar}
  resizeMode="cover"
  onError={(e) => console.warn(e.nativeEvent.error)}
/>

// Android XML drawable (0.78+) — same Image API
<Image source={require('./drawable/ic_notification.xml')} style={styles.icon} />

const styles = StyleSheet.create({
  icon: { width: 24, height: 24 },
  avatar: { width: 48, height: 48, borderRadius: 24 },
});
```

---

#### `ScrollView` — scroll all children (small lists only)

```tsx
import { ScrollView, RefreshControl, KeyboardAvoidingView, Platform } from 'react-native';

<KeyboardAvoidingView
  style={{ flex: 1 }}
  behavior={Platform.OS === 'ios' ? 'padding' : undefined}
  keyboardVerticalOffset={Platform.OS === 'ios' ? 64 : 0}
>
  <ScrollView
    style={{ flex: 1 }}
    contentContainerStyle={{ padding: 16, flexGrow: 1 }}
    keyboardShouldPersistTaps="handled"
    showsVerticalScrollIndicator={false}
    refreshControl={
      <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
    }
  >
    {children}
  </ScrollView>
</KeyboardAvoidingView>

// Horizontal chips
<ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
  {chips.map((c) => <Chip key={c.id} label={c.label} />)}
</ScrollView>
```

---

#### `FlatList` — virtualized list (default for long data)

```tsx
import { FlatList, ListRenderItem } from 'react-native';
import { useCallback, useMemo } from 'react';

type Item = { id: string; title: string };

function ItemList({ data }: { data: Item[] }) {
  const renderItem: ListRenderItem<Item> = useCallback(
    ({ item }) => <Row title={item.title} />,
    [],
  );

  const keyExtractor = useCallback((item: Item) => item.id, []);

  const ListEmpty = useMemo(
    () => () => <Text>No results</Text>,
    [],
  );

  return (
    <FlatList
      data={data}
      keyExtractor={keyExtractor}
      renderItem={renderItem}
      ListEmptyComponent={ListEmpty}
      ListHeaderComponent={<SearchBar />}
      ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: '#eee' }} />}
      // Performance
      initialNumToRender={10}
      maxToRenderPerBatch={10}
      windowSize={5}
      removeClippedSubviews={Platform.OS === 'android'}
      getItemLayout={(_, index) => ({
        length: ROW_HEIGHT,
        offset: ROW_HEIGHT * index,
        index,
      })}
      // Pull to refresh + infinite scroll
      refreshing={loading}
      onRefresh={refetch}
      onEndReached={loadMore}
      onEndReachedThreshold={0.3}
    />
  );
}
```

---

#### `SectionList` — grouped sections

```tsx
import { SectionList } from 'react-native';

const sections = [
  { title: 'A', data: ['Alice', 'Anna'] },
  { title: 'B', data: ['Bob'] },
];

<SectionList
  sections={sections}
  keyExtractor={(item, index) => item + index}
  renderItem={({ item }) => <Text style={{ padding: 12 }}>{item}</Text>}
  renderSectionHeader={({ section: { title } }) => (
    <View style={{ backgroundColor: '#f0f0f0', padding: 8 }}>
      <Text style={{ fontWeight: '700' }}>{title}</Text>
    </View>
  )}
  stickySectionHeadersEnabled
/>
```

---

#### `TextInput` — controlled input, validation, focus

```tsx
import { TextInput, View, StyleSheet } from 'react-native';
import { useRef, useState } from 'react';

function LoginForm() {
  const [email, setEmail] = useState('');
  const passwordRef = useRef<TextInput>(null);

  return (
    <View style={styles.form}>
      <TextInput
        style={styles.input}
        value={email}
        onChangeText={setEmail}
        placeholder="Email"
        keyboardType="email-address"
        autoCapitalize="none"
        autoCorrect={false}
        textContentType="emailAddress"
        returnKeyType="next"
        onSubmitEditing={() => passwordRef.current?.focus()}
      />
      <TextInput
        ref={passwordRef}
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        textContentType="password"
        returnKeyType="done"
        onSubmitEditing={submit}
      />
      <TextInput
        style={[styles.input, styles.multiline]}
        multiline
        numberOfLines={4}
        textAlignVertical="top"
        placeholder="Bio"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  form: { gap: 12 },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
  },
  multiline: { minHeight: 100 },
});
```

---

#### `Pressable` — preferred touch target (replaces TouchableOpacity*)

```tsx
import { Pressable, Text, StyleSheet } from 'react-native';

<Pressable
  onPress={() => {}}
  onLongPress={() => {}}
  disabled={loading}
  hitSlop={8}
  pressRetentionOffset={12}
  style={({ pressed }) => [
    styles.button,
    pressed && styles.buttonPressed,
    loading && styles.buttonDisabled,
  ]}
  accessibilityRole="button"
  accessibilityState={{ disabled: loading }}
>
  <Text style={styles.buttonLabel}>{loading ? 'Loading…' : 'Submit'}</Text>
</Pressable>

const styles = StyleSheet.create({
  button: {
    backgroundColor: '#0066cc',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonPressed: { opacity: 0.85 },
  buttonDisabled: { opacity: 0.5 },
  buttonLabel: { color: '#fff', fontWeight: '600' },
});
```

---

#### `Modal` — native modal layer

```tsx
import { Modal, View, Pressable, StyleSheet } from 'react-native';

<Modal
  visible={open}
  animationType="slide"
  presentationStyle="pageSheet" // iOS: pageSheet | formSheet | fullScreen
  transparent={false}
  onRequestClose={() => setOpen(false)} // Android back button
>
  <View style={styles.modalScreen}>
    <Pressable onPress={() => setOpen(false)}>
      <Text>Close</Text>
    </Pressable>
  </View>
</Modal>

// Transparent overlay modal
<Modal visible={open} transparent animationType="fade" onRequestClose={close}>
  <Pressable style={styles.backdrop} onPress={close}>
    <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
      {/* sheet content — stopPropagation prevents backdrop close */}
    </Pressable>
  </Pressable>
</Modal>
```

---

#### `Switch` — boolean toggle

```tsx
import { Switch, View, Text } from 'react-native';

<View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
  <Switch
    value={enabled}
    onValueChange={setEnabled}
    trackColor={{ false: '#ccc', true: '#81b0ff' }}
    thumbColor={enabled ? '#0066cc' : '#f4f4f4'}
  />
  <Text>Notifications</Text>
</View>
```

---

#### `ActivityIndicator` — loading spinner

```tsx
import { ActivityIndicator, View } from 'react-native';

<View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
  <ActivityIndicator size="large" color="#0066cc" />
</View>
```

---

#### `StatusBar` — system bar (per screen)

```tsx
import { StatusBar, Platform } from 'react-native';

<>
  <StatusBar
    barStyle="dark-content"
    backgroundColor={Platform.OS === 'android' ? '#ffffff' : undefined}
    translucent={false}
  />
  {/* screen */}
</>
```

---

#### `Keyboard` & `KeyboardAvoidingView`

```tsx
import { Keyboard, KeyboardAvoidingView, Platform, TouchableWithoutFeedback } from 'react-native';

// Dismiss keyboard on outside tap
<TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
  <View style={{ flex: 1 }}>{/* form */}</View>
</TouchableWithoutFeedback>

// Listen to keyboard height (custom layout)
import { useEffect, useState } from 'react';

useEffect(() => {
  const show = Keyboard.addListener('keyboardDidShow', (e) => {
    setKeyboardHeight(e.endCoordinates.height);
  });
  const hide = Keyboard.addListener('keyboardDidHide', () => setKeyboardHeight(0));
  return () => { show.remove(); hide.remove(); };
}, []);
```

---

#### `Animated` — timing, spring, native driver

```tsx
import { Animated, Pressable } from 'react-native';
import { useRef } from 'react';

function FadeInBox() {
  const opacity = useRef(new Animated.Value(0)).current;

  const fadeIn = () => {
    Animated.timing(opacity, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true, // opacity + transform only (classic rule)
    }).start();
  };

  return (
    <Pressable onPress={fadeIn}>
      <Animated.View style={{ opacity, transform: [{ scale: opacity }] }}>
        <Text>Animated</Text>
      </Animated.View>
    </Pressable>
  );
}

// Spring
Animated.spring(translateY, {
  toValue: 0,
  useNativeDriver: true,
  bounciness: 8,
}).start();
```

```tsx
// Modern hook API
import { useAnimatedValue, Animated } from 'react-native';

const width = useAnimatedValue(100);
Animated.timing(width, { toValue: 200, duration: 400, useNativeDriver: false }).start();
```

---

#### `LayoutAnimation` — easy layout transitions (enable on Android)

```tsx
import { LayoutAnimation, UIManager, Platform, Pressable } from 'react-native';

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const toggle = () => {
  LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
  setExpanded((e) => !e);
};
```

---

#### `Linking` — deep links & external URLs

```tsx
import { Linking, Alert } from 'react-native';
import { useEffect } from 'react';

// Open URL
const open = async (url: string) => {
  const supported = await Linking.canOpenURL(url);
  if (supported) await Linking.openURL(url);
  else Alert.alert('Cannot open URL');
};

// Handle incoming deep link
useEffect(() => {
  const sub = Linking.addEventListener('url', ({ url }) => {
    // parse url → navigate
  });
  Linking.getInitialURL().then((url) => url && /* cold start route */);
  return () => sub.remove();
}, []);
```

---

#### `AppState` — foreground / background

```tsx
import { AppState } from 'react-native';
import { useEffect, useRef } from 'react';

useEffect(() => {
  const sub = AppState.addEventListener('change', (nextState) => {
    if (nextState === 'active') refetch();
    if (nextState === 'background') pauseMedia();
  });
  return () => sub.remove();
}, []);
```

---

#### `Appearance` / `useColorScheme` — light & dark

```tsx
import { useColorScheme, Appearance } from 'react-native';

function ThemedScreen() {
  const scheme = useColorScheme(); // 'light' | 'dark' | null
  const bg = scheme === 'dark' ? '#000' : '#fff';

  useEffect(() => {
    const sub = Appearance.addChangeListener(({ colorScheme }) => {
      // react to system theme change
    });
    return () => sub.remove();
  }, []);

  return <View style={{ flex: 1, backgroundColor: bg }} />;
}
```

---

#### `Platform` — OS branching & version checks

```tsx
import { Platform, StyleSheet } from 'react-native';

const styles = StyleSheet.create({
  card: {
    padding: 16,
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 4 },
      android: { elevation: 4 },
      default: {},
    }),
  },
});

if (Platform.OS === 'android' && Platform.Version >= 33) {
  // API-level-specific logic
}

// Platform-specific files: Component.ios.tsx | Component.android.tsx
```

---

#### `Dimensions` / `useWindowDimensions`

```tsx
import { useWindowDimensions } from 'react-native';

function ResponsiveGrid() {
  const { width, height, scale, fontScale } = useWindowDimensions();
  const columns = width > 600 ? 3 : 2;
  return <View>{/* lay out by columns */}</View>;
}
```

---

#### `PixelRatio` — dp vs physical pixels

```tsx
import { PixelRatio, StyleSheet } from 'react-native';

const hairline = StyleSheet.hairlineWidth; // thinnest line on device
const px = PixelRatio.getPixelSizeForLayoutSize(8); // 8dp → px
const fontScale = PixelRatio.getFontScale(); // accessibility
```

---

#### `StyleSheet` — compose, absolute fill, transforms

```tsx
import { StyleSheet, View } from 'react-native';

const styles = StyleSheet.create({
  base: { padding: 8 },
  active: { backgroundColor: '#e6f2ff' },
  absoluteCenter: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: [{ translateX: -50 }, { translateY: -50 }],
  },
});

<View style={[styles.base, isActive && styles.active]} />
<View style={StyleSheet.absoluteFill} /> // full bleed overlay
```

---

#### `BackHandler` — Android hardware back

```tsx
import { BackHandler } from 'react-native';
import { useEffect } from 'react';

useEffect(() => {
  const sub = BackHandler.addEventListener('hardwareBackPress', () => {
    if (canGoBack) { goBack(); return true; } // consumed
    return false; // default behavior (exit app)
  });
  return () => sub.remove();
}, [canGoBack]);
```

---

#### `Alert` — native alert dialog

```tsx
import { Alert } from 'react-native';

Alert.alert('Delete item?', 'This cannot be undone.', [
  { text: 'Cancel', style: 'cancel' },
  { text: 'Delete', style: 'destructive', onPress: () => remove(id) },
]);
```

---

#### Native modules (bridge / TurboModule mental model)

```tsx
import { NativeModules, Platform } from 'react-native';

const { MyTurboModule, SettingsManager } = NativeModules;

// Promise-based native method
async function read() {
  const value = await MyTurboModule.getValue('key');
  return value;
}

// Platform split
const Module = Platform.select({
  ios: NativeModules.IOSMyModule,
  android: NativeModules.AndroidMyModule,
});
```

---

#### New Architecture opt-in (historical — pre-0.76 only)

```properties
# android/gradle.properties
newArchEnabled=true
```

```bash
# iOS
RCT_NEW_ARCH_ENABLED=1 bundle exec pod install
```

> **0.82+:** New Architecture cannot be disabled. Migrate on 0.81 first if coming from Legacy.

---

## Part 2: Version History — Features by Release

Releases ship on a **~8 week** cadence ([release schedule](https://reactnative.dev/docs/releases)). Patch releases fix regressions; minors add features. Below: **landmark features per minor**; patch-only fixes omitted unless critical.

> **Exhaustive raw changelogs:** [facebook/react-native releases](https://github.com/facebook/react-native/releases) · Historical aggregated changelogs: [react-native-community/releases](https://github.com/react-native-community/releases) (through ~0.57)

---

### Era: Genesis (2015–2016) — v0.1.x – v0.39.x

| Version | Date (approx) | Landmark features |
|---------|---------------|-------------------|
| **0.1.0** | Mar 2015 | First public release; **iOS only**; `React` package; async bridge to UIKit; announced at React Conf March 2015 |
| **0.2–0.11** | 2015 | Iterative iOS stability; npm distribution; dev tooling improvements |
| **0.12.0** | Sep 2015 | **Android support** ships |
| **0.13–0.20** | 2015–2016 | Android parity work; `Navigator` era APIs; packager improvements |
| **0.14–0.16** | 2016 | Hot reloading improvements; `AppRegistry` patterns |
| **0.20–0.25** | 2016 | **`ListView`** ecosystem; **`FlatList` / `SectionList` / `VirtualizedList`** introduced (0.24–0.25) replacing ListView patterns |
| **0.26–0.28** | 2016 | Layout improvements; percentage dimensions support expanded |
| **0.29–0.33** | 2016 | RN open-sourced on GitHub; community growth; Windows experimental efforts externalized |
| **0.34–0.39** | 2016 | **`KeyboardAvoidingView`**; improved touch handling; gradual removal of legacy Navigators from core docs |

---

### Era: Maturity (2017–2018) — v0.40.x – v0.59.x

| Version | Landmark features |
|---------|-------------------|
| **0.40** | **Breaking:** iOS project structure (`ios/` folder rename from `React`); migration pain point |
| **0.42–0.43** | Virtualized lists improvements; snapshot testing docs |
| **0.44** | **`FlatList`** promoted as default list solution |
| **0.45–0.46** | Percentage widths in flex; YellowBox improvements |
| **0.47** | **Breaking:** Android Gradle / support library bumps; `PropTypes` migration pressure |
| **0.48–0.49** | ESLint in template; Flow types emphasis |
| **0.50** | **`SafeAreaView`** (iOS notch era); **Babel 7** prep; `create-react-native-app` / Expo alignment |
| **0.51** | **`FlatList`** fixes; deprecations for legacy list APIs |
| **0.52** | **WKWebView** prep; TypeScript community templates; **React 16.2** |
| **0.53** | **Android TV** improvements; **Node 8+** |
| **0.54** | **Interactive docs**; **`propTypes` deprecation** accelerated; **React 16.4** |
| **0.55** | **Lean Core** begins — move non-core to community; **Geolocation** removed from core; Android tooling updates |
| **0.56** | **Babel 7** default; **Node 8** min; **Gradle 3.x / Android SDK 26** compile; **iOS 9** min; **React 16.4**; Fabric mentioned in blog (experimental internal) |
| **0.57** | Extended RC; **accessibility** overhaul; **WKWebView** opt-in for `WebView`; **Android overflow** support; **TypeScript** via Babel 7 in Metro; SDK 27 |
| **0.58** | Stability; bridge instrumentation; dependency bumps |
| **0.59** | **`react-native init` → CLI**; **JavaScriptCore** improvements; **Hermes** announced externally (not default); **`useNativeDriver`** emphasis; **`react-native.config.js`** for autolinking prep |

---

### Era: Autolinking & DX (2019–2020) — v0.60.x – v0.64.x

| Version | Landmark features |
|---------|-------------------|
| **0.60** | **AndroidX** migration; **CocoaPods** default iOS integration; **Autolinking** — no manual `react-native link`; **`use_frameworks!`** issues (fixed 0.61); iOS project structure changes |
| **0.61** | **Fast Refresh** (replaces live/hot reload split); **`useWindowDimensions`**; removed `React.xcodeproj` subproject flow; iOS CocoaPods unified |
| **0.62** | **Flipper** default; **`Appearance` / `useColorScheme`** (dark mode); **LogBox** opt-in; **React DevTools v4**; **PropTypes removed** from core components; Apple TV → `react-native-tvos`; Upgrade Support repo |
| **0.63** | **LogBox** default; **Pressable**; **iOS 13** SDK requirements; YellowBox APIs deprecated; tvOS split maintained |
| **0.64** | **Hermes on iOS** (opt-in); **Hermes proxy** support; **Inline Requires** default; **React 17** / new JSX transform; Hermes profiling in Chrome; dropped Android API 16–20; Xcode 12 |

---

### Era: New Architecture Seeds (2021–2022) — v0.65.x – v0.71.x

| Version | Landmark features |
|---------|-------------------|
| **0.65** | Hermes GC improvements; **`onPressIn`/`onPressOut` on `Text`**; **`stickyHeaderHiddenOnScroll`**; accessibility fixes; Intl on Android Hermes |
| **0.66** | **Android 12** support; **iOS 15** SDK; **`removeClippedSubviews`** default false; **React 17.0.2**; **propTypes** cleanup continues; **`SegmentedComponentIOS`** removed |
| **0.67** | **Gradle 7.2**, **Kotlin 1.5**; **DatePickerAndroid** lean-core removal; release tester program |
| **0.68** | **New Architecture opt-in** (Fabric + TurboModules); **React 18 not fully** on old arch; Node 16; AGP 7; Android API 31 target; NDK auto-download; docs “Architecture” section |
| **0.69** | **React 18** default (needs New Arch for concurrent); **Hermes bundled** with RN (version locked); **`.xcode.env`**; C++17; Android 11 status bar API; **M1** Android build fixes |
| **0.70** | **Hermes default** on new projects; **Codegen** unified `package.json` config; **CMake** default for Android native; **New Arch autolinking** Android; New Arch docs refresh; Metro 0.72 |
| **0.71** | **TypeScript by default** in template; **built-in TS types** — deprecate `@types/react-native`; **Flexbox `gap`**; propTypes temporarily restored for migration; Hermes bumps; **`react-native init`** still present |

---

### Era: Bridgeless & Stabilization (2023–2024) — v0.72.x – v0.76.x

| Version | Landmark features |
|---------|-------------------|
| **0.72** | Metro **symlinks** (beta) & **package exports** (beta); invalid style props **no redbox**; Hermes **ES2022** features (`Array.at`, `AggregateError`); **@react-native/** scoped packages rename; deprecated component removals; New Arch updates in working group |
| **0.73** | **Bridgeless Mode** (experimental); **Native Module Interop**; **Stable symlink** support; **Android 14**; **TypeScript** in core — deprecate `@types/react-native`; **debugging** improvements; **metro.config.js** format required; legacy remote JS debugging deprecated |
| **0.74** | **Yoga 3.0**; **Bridgeless default** when New Arch on; **batched `onLayout`**; **Yarn 3** default for new projects; **PropTypes removed**; **`PushNotificationIOS`** removed; min Android **API 23**; Metro 0.74 |
| **0.75** | **Yoga 3.1** — **`%` in gap & translate**; New Arch stabilization; **`/template` moved** to `react-native-community/template`; **`react-native init` sunset** announced (Dec 2024); recommend **Expo** as framework; last version minSdk 23 / iOS 13.4 |
| **0.76** | **New Architecture DEFAULT**; **React Native DevTools** stable; **Metro resolver ~15× faster**; **`boxShadow` & `filter`** (New Arch); **CLI decoupled** from `react-native` package; **Android `libreactnative.so` merge** (~3.8 MB smaller); min **iOS 15.1**, **Android API 24**; removed `@react-native-community/cli` as direct dep |

---

### Era: React 19 & Legacy Removal (2025–2026) — v0.77.x – 0.86 (RC)

| Version | Release (approx) | Landmark features |
|---------|------------------|-------------------|
| **0.77** | Jan 2025 | **`display: contents`**, **`boxSizing`**, **`mixBlendMode`**, **`outline*`** (New Arch); **Android 15 / 16 KB page** support; **Swift** default iOS template + **`RCTAppDependencyProvider`**; **`react-native init` fully deprecated**; Metro **`console.log` streaming removed**; Kotlin **2.0.21**; sticky header / absolute positioning fixes |
| **0.78** | Feb 2025 | **React 19** in RN; **Android XML vector drawables** in `Image`; **`ReactNativeFactory`** iOS brownfield; Metro **JS logs opt-in**; smaller release artifacts |
| **0.79** | Apr 2025 | **Metro 0.82** — deferred hashing (~3× faster start); **`package.json` exports/imports** default; **JSC → community package**; **Swift-compatible native modules**; Android **uncompressed JS bundle** (faster startup); **Remote JS debugging removed**; internal **ESM exports** |
| **0.80** | Jun 2025 | **React 19.1.0**; **Legacy Architecture frozen** (warnings); **deep imports deprecated**; **Strict TypeScript API** opt-in; experimental **precompiled iOS** deps |
| **0.81** | Aug 2025 | **Android 16 (API 36)** default target; **edge-to-edge** required; **`SafeAreaView` deprecated**; **JSC removed from core**; **experimental precompiled iOS** (~10× compile); **Node 20.19.4+**, **Xcode 16.1+**; **`RN_SERIALIZABLE_STATE`** for Fabric; better uncaught error reporting |
| **0.82** | Oct 2025 | **New Architecture ONLY** — cannot disable; **Hermes V1 experimental** opt-in; **React 19.1.1** + owner stacks; **DOM-like node APIs** on refs; **Web Performance APIs** (Canary); **`debugOptimized`** Android build; uncaught **promise rejections** surface; Gradle **9** |
| **0.83** | Dec 2025 | **First release with zero user-facing breaking changes** (from 0.82); **React 19.2** (`<Activity>`, `useEffectEvent`); **DevTools**: Network + Performance panels, **desktop app**; **IntersectionObserver** (Canary); **Performance APIs stable**; Hermes V1 experimental improvements; **`RCT_REMOVE_LEGACY_ARCH`** experimental iOS flag |
| **0.84** | Feb 2026 | **Hermes V1 DEFAULT**; **precompiled iOS binaries DEFAULT**; **Legacy Arch code stripped** (iOS default, Android class removals); **Node 22.11+** min; **React 19.2.3**; **ESLint v9 flat config**; HEIC/HEIF images; Android **`onKeyDown`/`onKeyUp`**; URL/URLSearchParams completeness; Text `onPress` → `accessibilityRole="link"` |
| **0.85** | Apr 2026 | **Shared Animation Backend** (with Software Mansion) — layout props with native driver in Animated; **`@react-native/jest-preset`** extracted; **DevTools**: multi-CDP, macOS tabs, network payload previews; **Metro TLS** for HTTPS dev; drops EOL Node; **`StyleSheet.absoluteFillObject` removed**; YogaNode → Kotlin on Android |
| **0.86** | RC mid-2026 | **View Transition APIs** / `unstable_ViewTransitionName`; Text **`boxShadow`** E2E; Filter support tests; Hermes compiler bumps; DevTools derive WebSocket from dev server URL (HTTPS); Bridgeless Choreographer fixes; continued Legacy removal |

---

### Future (Scheduled — reactnative.dev/versions)

| Version | Branch cut (planned) | Notes |
|---------|---------------------|-------|
| **0.87.x** | Jul 2026 | Future |
| **0.88.x** | Sep 2026 | Future |
| **0.89.x** | Nov 2026 | Future |

---

## Appendix A: New Architecture Timeline (Interview)

| Milestone | Version |
|-----------|---------|
| Fabric/TurboModules announced | 2018 blog (“State of RN”) |
| Experimental opt-in | **0.68** (Mar 2022) |
| Bridgeless introduced | **0.73** (Dec 2023) |
| Bridgeless default (with New Arch) | **0.74** (Apr 2024) |
| New Arch default | **0.76** (Oct 2024) |
| Legacy frozen | **0.80** (Jun 2025) |
| New Arch mandatory | **0.82** (Oct 2025) |
| Legacy code removal ongoing | **0.84+** |

---

## Appendix B: Hermes Timeline

| Milestone | Version |
|-----------|---------|
| Introduced (Android opt-in) | ~0.60 era |
| iOS opt-in | **0.64** |
| Default new projects | **0.70** |
| Bundled with RN | **0.69** |
| Hermes V1 experimental | **0.82** |
| Hermes V1 default | **0.84** |

---

## Appendix C: Key Breaking Changes to Remember

| Version | Breaking change |
|---------|-----------------|
| 0.40 | iOS folder restructure |
| 0.47 | Android Gradle / tooling |
| 0.56 | Babel 7, Node 8, iOS 9 |
| 0.60 | AndroidX, autolinking, CocoaPods |
| 0.62 | PropTypes removed (core) |
| 0.64 | Android min API 21→23 later in 0.74; inline requires default |
| 0.74 | PropTypes gone; PushNotificationIOS removed; API 23 min |
| 0.75 | init sunset path; min platform bumps next |
| 0.76 | New Arch default; CLI separate package; iOS 15.1 / API 24 |
| 0.77 | Metro log streaming gone; Swift template |
| 0.79 | Remote debugging removed; JSC external |
| 0.81 | SafeAreaView deprecated; JSC out of core |
| 0.82 | Cannot disable New Arch |
| 0.84 | Node 22; Hermes V1 default |
| 0.85 | Jest preset package; absoluteFillObject removed |

---

## Appendix D: Recommended Learning Path (Pre-Interview)

1. Build a small app with **React Navigation** + **FlatList** + **native module** call  
2. Enable **New Architecture** on 0.81, upgrade mentally to 0.82 constraints  
3. Trace one screen in **React Native DevTools** (Performance + Network)  
4. Read **Upgrade Helper** diff 0.76 → 0.85 for migration vocabulary  
5. Skim **Fabric renderer** and **TurboModules** docs on reactnative.dev/architecture  

---

## Appendix E: Official Blog Index (Release Posts)

Use for deeper reading per version:

- [0.60](https://reactnative.dev/blog/2019/07/03/version-60) · [0.61](https://reactnative.dev/blog/2019/09/18/version-0.61) · [0.62](https://reactnative.dev/blog/2020/03/26/version-0.62) · [0.63](https://reactnative.dev/blog/2020/07/06/version-0.63) · [0.64](https://reactnative.dev/blog/2021/03/12/version-0.64)
- [0.67](https://reactnative.dev/blog/2022/01/19/version-067) · [0.68](https://reactnative.dev/blog/2022/03/30/version-068) · [0.69](https://reactnative.dev/blog/2022/06/21/version-069) · [0.70](https://reactnative.dev/blog/2022/09/05/Version-070) · [0.71](https://reactnative.dev/blog/2023/01/12/version-071)
- [0.72](https://reactnative.dev/blog/2023/06/21/0.72-metro-package-exports-symlinks) · [0.73](https://reactnative.dev/blog/2023/12/06/0.73-debugging-improvements-stable-symlinks) · [0.74](https://reactnative.dev/blog/2024/04/22/release-0.74) · [0.75](https://reactnative.dev/blog/2024/08/12/release-0.75) · [0.76](https://reactnative.dev/blog/2024/10/23/release-0.76-new-architecture)
- [0.77](https://reactnative.dev/blog/2025/01/21/version-0.77) · [0.78](https://reactnative.dev/blog/2025/02/19/react-native-0.78) · [0.79](https://reactnative.dev/blog/2025/04/08/react-native-0.79) · [0.80](https://reactnative.dev/blog/2025/06/12/react-native-0.80) · [0.81](https://reactnative.dev/blog/2025/08/12/react-native-0.81)
- [0.82](https://reactnative.dev/blog/2025/10/08/react-native-0.82) · [0.83](https://reactnative.dev/blog/2025/12/10/react-native-0.83) · [0.84](https://reactnative.dev/blog/2026/02/11/react-native-0.84) · [0.85](https://reactnative.dev/blog/2026/04/07/react-native-0.85)

**Archive (pre-0.60 docs):** [archive.reactnative.dev](https://archive.reactnative.dev/)

---

*Cheatsheet compiled from React Native official blogs, release notes, and changelogs. Patch-level changes and reverted commits are omitted for readability; verify critical migrations against the Upgrade Helper for your target version.*
