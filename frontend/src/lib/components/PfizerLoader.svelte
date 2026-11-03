<!-- @deprecated Prefer OrthosLoader — kept as a thin alias for older imports. -->
<script>
  import OrthosLoader from './OrthosLoader.svelte';
  let { label = 'Loading' } = $props();
</script>

<OrthosLoader {label} />
