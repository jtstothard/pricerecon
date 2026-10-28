import { useContext, useState } from 'react'
import { OfflineImageContext } from './OfflineImages'

type Image = {
  kind: 'photo' | 'illustration' | 'original_placeholder' | 'remote_reference'
  configuration_note?: string
  source_context_url?: string
  url: string | null
  attribution: string
  provenance: string
  permission_reference: string | null
  identity_reference: string | null
}

export default function DiscoveryImage({
  image,
  compact = false,
}: {
  image: Image
  compact?: boolean
}) {
  const [failed, setFailed] = useState(false)
  const localAssets = useContext(OfflineImageContext)
  const displayUrl = localAssets === null ? image.url : localAssets.get(image.url ?? '')
  const reference = image.kind === 'remote_reference'
  const available = image.kind !== 'original_placeholder' && displayUrl && !failed
  return (
    <figure className="discovery-picture">
      {available ? (
        <img
          src={displayUrl ?? undefined}
          alt={
            reference
              ? `Reference watch: ${image.configuration_note}`
              : image.kind === 'photo'
                ? 'Photograph of the depicted watch'
                : 'Illustration of the depicted watch'
          }
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
        />
      ) : (
        <p>Product image unavailable. Generic placeholder; does not depict this watch.</p>
      )}
      <figcaption>
        {available
          ? reference
            ? 'Remote reference image; exact configuration not established'
            : image.kind === 'photo'
              ? 'Photograph'
              : 'Product illustration; not a photograph'
          : 'Placeholder'}
        {reference && !compact && <p>{image.configuration_note}</p>}
        {!compact && (
          <section>
            <h3>Image source and attribution</h3>
            <p>{image.attribution}</p>
            <p>{image.provenance}</p>
            {reference && (
              <p>
                Remote display only; no licence or buying qualification claimed.
                <br />
                <a href={image.source_context_url} target="_blank" rel="noreferrer">
                  Original source and attribution context
                </a>
                {' · '}
                <a href={image.url ?? undefined} target="_blank" rel="noreferrer">
                  Original image
                </a>
              </p>
            )}
            {available && !reference && (
              <section>
                <h3>Image evidence</h3>
                <p>
                  <a href={image.url ?? undefined} target="_blank" rel="noreferrer">
                    Original image
                  </a>
                </p>
                <p>Permission: {image.permission_reference}</p>
                <p>Depiction: {image.identity_reference}</p>
              </section>
            )}
          </section>
        )}
      </figcaption>
    </figure>
  )
}
